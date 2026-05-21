# Save logic for the DB
# Checks hash for deduplication
# Saves `RSSItem` list into the db
# I will rewrite comments in english a bit later


from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from log.log import logger
from database.models import Channel, Post
from client.rss import RSSItem


class NewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_channel(self, username: str) -> Channel:
        stmt = select(Channel).where(Channel.username == username)
        result = await self.session.execute(stmt)
        channel = result.scalar_one_or_none()

        if not channel:
            logger.info("Database | Adding new channel to monitor: @%s", username)
            channel = Channel(username=username, title=username)
            self.session.add(channel)
            await self.session.flush()
        
        return channel

    async def save_rss_items(self, items: list[RSSItem]) -> int:
        # Сохраняет список RSSItem в базу данных.
        # Пропускает дубликаты по post_hash.
        # Возвращает количество успешно добавленных новых постов.
        if not items:
            return 0

        saved_count = 0

        # Кэш для каналов в рамках одной пачки, чтобы не трогать базу на каждый пост
        channel_cache: dict[str, int] = {}

        for item in items:
            if not item.source_name:
                continue

            username = item.source_name.lower()

            # Получаем ID канала (из кэша или из базы)
            if username in channel_cache:
                channel_id = channel_cache[username]
            else:
                channel = await self.get_or_create_channel(username)
                channel_id = channel.id
                channel_cache[username] = channel_id

            # дедупликация
            stmt = insert(Post).values(
                channel_id=channel_id,
                entry_id=item.entry_id,
                post_hash=item.hash,
                title=item.title,
                text=item.text,
                link=item.link,
                image_urls=item.image_urls,
                published_at=item.published_at,
                fetched_at=item.fetched_at,
                is_summarized=False
            ).on_conflict_do_nothing(index_elements=['post_hash'])

            result = await self.session.execute(stmt)
            
            if result.rowcount > 0:
                saved_count += 1

        if saved_count > 0:
            await self.session.commit()
            logger.info("Database | Successfully saved %d new posts to DB", saved_count)
        else:
            await self.session.rollback()

        return saved_count
    # комменты же на английском были везде, ладно