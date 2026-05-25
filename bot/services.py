# Connecting the main backend(data collection) to the UI(bot)
# Gets posts from db + RSS and sends to user

from __future__ import annotations

import io
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import User, Post, Channel
from process.filter import NewsFilter
from process.ai import GeminiSummarizer
from main import run_parser_for_channels 


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
            from log.log import logger
            logger.error(f"Parser Error during manual trigger for user {tg_id}: {e}")

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
        ai_xml_input = news_filter.format_for_ai(filtered_posts)
        
        try:
            summarizer = GeminiSummarizer(api_key=user_plain_key)
            ai_summary_text = await summarizer.generate_summary(ai_xml_input)
            return ai_summary_text
        except Exception as e:
            from log.log import logger
            logger.error(f"SERVICE | Failed to generate AI summary: {e}")
            return None