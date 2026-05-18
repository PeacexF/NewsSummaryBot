import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient

API_ID = 2040
API_HASH = 'b1d2aa4942ecda3283f0821355522b11'

class NewsCollector:
    def __init__(self, session_name='android_session'):
        self.client = TelegramClient(session_name, API_ID, API_HASH)

    async def start(self):
        await self.client.start()
        print("Юзербот успешно авторизован и запущен.")

    async def stop(self):
        await self.client.disconnect()

    async def fetch_daily_news(self, channels_list):

        # словарь: {'имя_канала': [{'text': '...', 'date': ...}]}
        # Временная отметка: ровно 24 часа назад в UTC
        time_threshold = datetime.now(timezone.utc) - timedelta(days=1)
        news_data = {}

        for channel in channels_list:
            print(f"Сканирую канал: @{channel}...")
            news_data[channel] = []
            
            try:
                async for message in self.client.iter_messages(channel, limit=100):
                    if message.date < time_threshold:
                        break
                    
                    if message.text and len(message.text.strip()) > 0:
                        news_data[channel].append({
                            'text': message.text,
                            'date': message.date
                        })
            except Exception as e:
                print(f"Ошибка при чтении канала @{channel}: {e}")
                
        return news_data

if __name__ == '__main__':
    TEST_CHANNELS = ['durov']

    async def test():
        collector = NewsCollector()
        await collector.start()
        
        raw_news = await collector.fetch_daily_news(TEST_CHANNELS)
        
        print(f"\n собрано каналов: {len(raw_news)}")
        for ch, posts in raw_news.items():
            print(f"  @{ch}: найдено {len(posts)} постов за 24ч.")
            
        await collector.stop()

    asyncio.run(test())