import sys
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))   # to import properly

from rss import RSSCollector  
from log.log import logger
# from config import smth maybe later idk

load_dotenv(Path(__file__).parent.parent / ".env")
RSSHUB_BASE = os.getenv("RSSHUB_BASE")

CHANNELS = ["durov", "rbc_news", "cybers"]  # Паша разбань мне акк в тг!!!

async def main():
    collector = RSSCollector(timeout=30, max_connections=10)
    await collector.start()

    urls = [RSSHUB_BASE.format(channel=ch) for ch in CHANNELS]

    logger.info(f"Started fetching from rsshub")
    
    items = await collector.fetch_many(urls)
    
    time_threshold = datetime.now(timezone.utc) - timedelta(days=1) # last 24h
    fresh_posts = []

    for item in items:
        if item.published_at and item.published_at > time_threshold:
            fresh_posts.append(item)

    logger.info(f"Total posts: {len(items)}")
    logger.info(f"Last 24h: {len(fresh_posts)}")

    for i, post in enumerate(fresh_posts[:3], 1):   # Test
        print(f"\n[{i}] Канал: @{post.source_name} | Дата: {post.published_at}")
        print(f"Текст: {post.text[:150]}...")

    await collector.close()

if __name__ == "__main__":
    asyncio.run(main())