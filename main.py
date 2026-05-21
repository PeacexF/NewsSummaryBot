import asyncio
import os

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from client.rss import RSSCollector  
from log.log import logger
from database.database import init_models, AsyncSessionLocal
from database.repository import NewsRepository


load_dotenv()
RSSHUB_BASE = os.getenv("RSSHUB_BASE")

CHANNELS = ["durov", "rbc_news", "cybers"]

async def main():
    logger.info("Initializing DB")
    await init_models()


    collector = RSSCollector(timeout=30, max_connections=10)

    await collector.start()
    urls = [RSSHUB_BASE.format(channel=ch) for ch in CHANNELS]

    logger.info(f"Started fetching from rsshub")
    items = await collector.fetch_many(urls)
    await collector.close()
    logger.info(f"Total posts fetched: {len(items)}")

    async with AsyncSessionLocal() as session:
        repo = NewsRepository(session)
        new_posts_inserted = await repo.save_rss_items(items)

"""
    time_threshold = datetime.now(timezone.utc) - timedelta(days=1) # last 24h
    fresh_posts = []

    for item in items:
        if item.published_at and item.published_at > time_threshold:
            fresh_posts.append(item)

    logger.info(f"Total posts: {len(items)}")
    logger.info(f"Last 24h: {len(fresh_posts)}")

    for i, post in enumerate(fresh_posts[:3], 1):   # Test
        print(f"\n[{i}] Канал: @{post.source_name} | Дата: {post.published_at}")
        print(f"Текст: {post.text}")
"""

if __name__ == "__main__":
    asyncio.run(main())