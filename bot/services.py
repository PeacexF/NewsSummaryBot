# Connecting the main backend(data collection) to the UI(bot)
# Gets posts from db + RSS and sends to user

from __future__ import annotations

import io
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import User, Post, Channel
from process.filter import NewsFilter
from process.ai import GeminiSummarizer
from main import run_parser_for_channels 
from log.log import logger


class SummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_user_txt_summary(self, tg_id: int) -> io.BytesIO | None:
        user_stmt = (
            select(User)
            .options(joinedload(User.channels))
            .where(User.id == tg_id)
        )
        user_res = await self.session.execute(user_stmt)
        user = user_res.unique().scalar_one_or_none()
        
        if not user or not user.channels:
            return None

        active_channels = [ch.username for ch in user.channels if ch.is_active]
        channel_ids = [ch.id for ch in user.channels]

        if not active_channels:
            return None

        try:
            await run_parser_for_channels(active_channels, self.session)
            await self.session.flush()
        except Exception as e:
            logger.error(f"SERVICE | Parser Error during manual trigger for user {tg_id}: {e}")

        time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        posts_stmt = (
            select(Post)
            .options(joinedload(Post.channel))
            .where(Post.channel_id.in_(channel_ids))
            .where(Post.is_summarized == False)
            .where(Post.fetched_at >= time_threshold)
            .order_by(Post.published_at.asc())
        )
        posts_res = await self.session.execute(posts_stmt)
        posts = posts_res.unique().scalars().all()

        if not posts:
            return None

        news_filter = NewsFilter(similarity_threshold=0.6, shingle_size=2)
        filtered_posts = news_filter.filter_duplicates(posts)

        if not filtered_posts:
            return None

        output = io.BytesIO()
        lines = []
        
        lines.append("=" * 60)
        lines.append(f"ПЕРВОИСТОЧНИКИ {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        lines.append("=" * 60 + "\n")

        for i, post in enumerate(filtered_posts, 1):
            date_str = post.published_at.strftime("%Y-%m-%d %H:%M") if post.published_at else "Без даты"
            
            lines.append(f"[{i}] Источник: @{post.channel.username} | Время: {date_str}")
            if post.title:
                lines.append(f"Заголовок: {post.title.strip()}")
            if post.link:
                lines.append(f"Ссылка: {post.link.strip()}")
            if post.text:
                lines.append(f"Текст:\n{post.text.strip()}")
            lines.append("-" * 50 + "\n")

        txt_content = "\n".join(lines)
        output.write(txt_content.encode("utf-8"))
        output.seek(0)
        
        user.last_summary_at = datetime.now(timezone.utc)
        
        for post in filtered_posts:
            post.is_summarized = True
            
        await self.session.commit()
        
        return output
    
    async def generate_ai_summary(self, filtered_posts: list[Post], user_plain_key: str) -> str | None:

        if not filtered_posts:
            return None

        news_filter = NewsFilter()

        sorted_posts = sorted(
            filtered_posts, 
            key=lambda p: p.channel.username.lower() if (p.channel and p.channel.username) else ""
        )

        chunk_size = 20
        posts_chunks = [sorted_posts[i:i + chunk_size] for i in range(0, len(sorted_posts), chunk_size)]
        
        logger.info(f"SERVICE | total posts for ai: {len(sorted_posts)}. packs of 20: {len(posts_chunks)}")

        xml_chunks = [news_filter.format_for_ai(chunk) for chunk in posts_chunks]

        try:
            summarizer = GeminiSummarizer(api_key=user_plain_key)

            valid_summaries = []

            for idx, xml_chunk in enumerate(xml_chunks, start=1):
                logger.info(f"SERVICE | sending to ai, pack num: {idx} out of {len(xml_chunks)}")
                
                summary_chunk = await summarizer.generate_chunk_summary(xml_chunk)
                
                if summary_chunk:
                    valid_summaries.append(summary_chunk)
                
                if idx < len(xml_chunks):
                    logger.info("SERVICE | Waiting to avoid rate limits...")
                    await asyncio.sleep(11.0)       # 5 RPM max -> 60 / 5 == 12
                                                    # Each request takes a second or two, so 12 - 1 == 11

            if not valid_summaries:
                logger.warning("SERVICE | No valid summaries returned.")
                return None

            final_summary_text = "\n\n".join(valid_summaries)
            return final_summary_text

        except Exception as e:
            logger.error(f"SERVICE | error: {e}")
            return None