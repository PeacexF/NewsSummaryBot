import asyncio
import hashlib
import logging
import html
import re
import aiohttp
import feedparser

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse
from __future__ import annotations


logger = logging.getLogger(__name__)    # should add better logging tbh


USER_AGENT = (
    "NewsSummaryBot "
    "(RSSHub Telegram Fetcher)"
)

HTML_TAG_RE = re.compile(r"<[^>]+>")    # for future

@dataclass(slots=True)
class RSSItem:
    source_url: str
    feed_title: str | None

    title: str | None
    text: str | None
    link: str | None

    published_at: datetime | None

    entry_id: str
    hash: str

    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RSSCollector:
#    Minimal async RSS collector.
#
#    Responsibilities:
#    - fetch RSS XML
#    - parse feed
#    - normalize entries
#    - return structured items
#
#    DOES NOT:
#    - summarize
#    - filter
#    - store to DB
#    - deduplicate globally

    def __init__(self, timeout: int = 20, max_connections: int = 20,):
        self.timeout = timeout
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            ssl=False,
        )

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if self.session:
            return

        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "User-Agent": USER_AGENT,
            },
        )

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def fetch_feed(self, url: str) -> list[RSSItem]:  # 1 single feed / url
        if not self.session:
            raise RuntimeError("RSSCollector.start() was not called")

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()

                content = await response.text()

        except Exception as e:
            logger.exception("Failed to fetch RSS feed: %s | error=%s", url, e,)
            return []

        parsed = feedparser.parse(content)

        feed_title = parsed.feed.get("title")

        items: list[RSSItem] = []

        for entry in parsed.entries:
            try:
                item = self._parse_entry(
                    source_url=url,
                    feed_title=feed_title,
                    entry=entry,
                )

                items.append(item)

            except Exception as e:
                logger.exception("Failed to parse RSS entry: %s | error=%s", url, e,)

        return items

    async def fetch_many(self ,urls: list[str]) -> list[RSSItem]:   # multiple
        tasks = [self.fetch_feed(url) for url in urls]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        all_items: list[RSSItem] = []

        for result in results:
            if isinstance(result, Exception):
                continue

            all_items.extend(result)

        return all_items

    def _parse_entry(self, source_url: str, feed_title: str | None, entry: Any) -> RSSItem:

        title = self._clean(entry.get("title"))
        summary = self._clean(entry.get("summary"))
        content = self._extract_content(entry)

        text = content or summary

        link = entry.get("link")

        entry_id = (
            entry.get("id")
            or entry.get("guid")
            or link
            or self._fallback_id(title, text)
        )

        published_at = self._parse_datetime(
            entry.get("published")
            or entry.get("updated")
        )

        item_hash = self._make_hash(
            title=title,
            text=text,
            link=link,
        )

        return RSSItem(
            source_url=source_url,
            feed_title=feed_title,

            title=title,
            text=text,
            link=link,

            published_at=published_at,

            entry_id=str(entry_id),
            hash=item_hash,

            raw=dict(entry),
        )

    @staticmethod
    def _extract_content(entry: Any) -> str | None:
        content = entry.get("content")

        if not content:
            return None
        if not isinstance(content, list):
            return None
        if not content:
            return None
        
        first = content[0]
        if not isinstance(first, dict):
            return None

        return first.get("value")

    @staticmethod
    def _clean(value: Any) -> str | None:
        if not value:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value

    @staticmethod
    def _parse_datetime(
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        try:
            dt = parsedate_to_datetime(value)

            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except Exception:
            return None

    @staticmethod
    def _fallback_id(
        title: str | None,
        text: str | None,
    ) -> str:

        base = f"{title or ''}:{text or ''}"

        return hashlib.sha256(
            base.encode("utf-8"),
        ).hexdigest()

    @staticmethod
    def _make_hash(
        title: str | None,
        text: str | None,
        link: str | None,
    ) -> str:

        base = (
            f"{title or ''}"
            f"{text or ''}"
            f"{link or ''}"
        )

        return hashlib.sha256(
            base.encode("utf-8"),
        ).hexdigest()



async def main():
    collector = RSSCollector()

    await collector.start()

    items = await collector.fetch_many([
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.bbci.co.uk/news/rss.xml",
    ])

    for item in items:
        print(item.to_dict())

    await collector.close()



if __name__ == "__main__":
    asyncio.run(main())