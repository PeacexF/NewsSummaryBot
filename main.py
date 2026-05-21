import asyncio
import os

from dotenv import load_dotenv

from client.rss import RSSCollector  
from log.log import logger
from database.database import init_models, AsyncSessionLocal
from database.repository import NewsRepository
from process.filter import NewsFilter


load_dotenv()
RSSHUB_BASE = os.getenv("RSSHUB_BASE")

CHANNELS = ["durov", "rbc_news", "cybers"]

async def main():
    logger.info("Initializing DB")
    await init_models()


    collector = RSSCollector(timeout=30, max_connections=10)

    await collector.start()
    urls = [RSSHUB_BASE.format(channel=ch) for ch in CHANNELS]

    logger.info(f"MAIN | Started fetching from rsshub")
    items = await collector.fetch_many(urls)
    await collector.close()
    logger.info(f"MAIN | Total posts fetched: {len(items)}")

    async with AsyncSessionLocal() as session:
        repo = NewsRepository(session)
        new_posts_inserted = await repo.save_rss_items(items)

    logger.info("MAIN | Starting deduplication process")

    async with AsyncSessionLocal() as session:
        news_filter = NewsFilter(similarity_threshold=0.6, shingle_size=2)
        
        raw_posts = await news_filter.get_fresh_posts(session)
        logger.info(f"MAIN | Unprocessed posts in DB: {len(raw_posts)}")
        
        filtered_posts = news_filter.filter_duplicates(raw_posts)
        logger.info(f"MAIN | Active posts remaining after deduplication: {len(filtered_posts)}")

        if not filtered_posts:
            logger.info("MAIN | No unique posts to display.")
            return

        # raw txt for user
        print("\n" + "="*50)
        print("TXT SOURCE FILE (NO DUPLICATES)")
        print("="*50 + "\n")
        
        for i, post in enumerate(filtered_posts, 1):
            # date
            date_str = post.published_at.strftime("%Y-%m-%d %H:%M") if post.published_at else "Без подписей без дат, но доклад вроде..."
            
            print(f"[{i}] Канал: @{post.channel.username} | Время: {date_str}")
            print(f"Текст: {post.text}")
            print("-" * 40)
            
        # testing XML
        print("\n" + "="*50)
        print("XML STRUCTURE FOR AI")
        print("="*50 + "\n")
        
        ai_xml_input = news_filter.format_for_ai(filtered_posts)
        print(ai_xml_input)

if __name__ == "__main__":
    asyncio.run(main())