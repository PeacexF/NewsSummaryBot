# This module reads and collects data from the rss stream
#
# class RSSCollector is then imported into run_collector.py
# Requires a self hosted RSSHub
# as it does not route it's requests through a proxy, doen't randomise User Agents and has no randomised request time
# Cloudflare just answers with 403 if you try to run it on a public instance of RSS

from __future__ import annotations

import aiohttp
import feedparser
import asyncio
import hashlib
import html
import re

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from log.log import logger              # Logging
from parser import HTMLContentParser    # Parser on bs4


USER_AGENT = (
    "NewsSummaryBot"
    "(RSSHub Telegram Collector)"
)


HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class RSSItem:
    source_url: str

    source_type: str
    source_name: str | None

    title: str | None

    text: str | None
    raw_html: str | None
    image_urls: list[str]

    link: str | None

    published_at: datetime | None
    fetched_at: datetime

    entry_id: str
    hash: str

    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RSSCollector:

    def __init__(self, timeout: int = 20, max_connections: int = 20) -> None:

        self.timeout = timeout

        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            ssl=False,
        )

        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:

        if self.session:
            return

        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": USER_AGENT}
        )

    async def close(self) -> None:

        if self.session:
            await self.session.close()

    async def fetch_feed(self, url: str) -> list[RSSItem]:

        if not self.session:
            raise RuntimeError("RSSCollector.start() was not called")

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()

                content = await response.text()

        except Exception as e:
            logger.info("RSS fetch failed | %s | %s", url, e)
            return []

        parsed = await asyncio.to_thread(feedparser.parse, content)
        # Turns out it's synchronous and severily bottlenecks everything here

        fetched_at = datetime.now(timezone.utc)

        feed_title = parsed.feed.get("title")

        items: list[RSSItem] = []

        for entry in parsed.entries:

            try:
                item = self._parse_entry(
                    source_url=url,
                    feed_title=feed_title,
                    entry=entry,
                    fetched_at=fetched_at,
                )

                items.append(item)

            except Exception as e:
                logger.info("RSS entry parse failed | %s | %s", url, e)

        return items

    async def fetch_many(self, urls: list[str]) -> list[RSSItem]:

        tasks = [self.fetch_feed(url) for url in urls]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: list[RSSItem] = []

        for result in results:

            if isinstance(result, Exception):
                logger.error("Fail in fetch_many %s", result)
                continue

            all_items.extend(result)

        return all_items

    def _parse_entry(self, source_url: str, feed_title: str | None, entry: Any, fetched_at: datetime) -> RSSItem:

        title = self._clean(entry.get("title"))

        raw_html = (entry.get("summary") or entry.get("description"))

        parse_result = HTMLContentParser.parse_entry_html(raw_html)
        clean_text = parse_result.clean_text
        image_urls = parse_result.image_urls

        link = entry.get("link")

        published_at = self._parse_datetime(
            entry.get("published")
            or entry.get("updated")
        )

        entry_id = (
            entry.get("id") or entry.get("guid") or link
            or self._fallback_id(
                title,
                clean_text,
            )
        )

        source_name = self._extract_source_name(source_url, link)

        item_hash = self._make_hash(
            title=title,
            text=clean_text,
        )

        return RSSItem(
            source_url=source_url,

            source_type="telegram_rsshub",
            source_name=source_name,

            title=title,

            text=clean_text,
            raw_html=raw_html,
            image_urls=image_urls,

            link=link,

            published_at=published_at,
            fetched_at=fetched_at,

            entry_id=str(entry_id),
            hash=item_hash,

            raw=dict(entry),
        )

    @staticmethod
    def _html_to_text(value: str | None) -> str | None:

        if not value:
            return None

        value = re.sub(
            r"<br\s*/?>",
            "\n",
            value,
            flags=re.I,
        )

        value = HTML_TAG_RE.sub("", value)

        value = html.unescape(value)

        value = value.strip()

        if not value:
            return None

        return value

    @staticmethod
    def _extract_source_name(source_url: str,post_url: str | None) -> str | None:

        if post_url:
            parsed = urlparse(post_url)

            path = parsed.path.strip("/")

            if path:
                return path.split("/")[0]

        if "/telegram/channel/" in source_url:
            return source_url.rstrip("/").split("/")[-1]

        return None

    @staticmethod
    def _clean(value: Any) -> str | None:

        if not value:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:

        if not value:
            return None

        try:
            dt = parsedate_to_datetime(value)

            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except Exception as e:
            logger.info(f"datetime error: {e}")

    @staticmethod
    def _fallback_id(title: str | None, text: str | None) -> str:

        base = f"{title or ''}:{text or ''}"

        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def _make_hash(title: str | None, text: str | None) -> str:

        normalized = (f"{title or ''}\n{text or ''}").lower()
        normalized = re.sub(r"\s+", " ", normalized)

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()