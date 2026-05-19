# HTML Parser on bs4 to extract images and urls from an rss stream

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from bs4 import BeautifulSoup


@dataclass(slots=True)
class ParsedHTMLResult:
    clean_text: str | None
    image_urls: list[str]


class HTMLContentParser:
    @staticmethod
    def parse_entry_html(raw_html: str | None) -> ParsedHTMLResult:
        # Clears tags, returns urls
        if not raw_html:
            return ParsedHTMLResult(clean_text=None, image_urls=[])

        html_content = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.I)

        soup = BeautifulSoup(html_content, "lxml")

        image_urls: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                image_urls.append(src.strip())

        # Formatting <a> tahs to save the urls for AI
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href")
            link_text = a_tag.get_text().strip()

            if href:
                href = href.strip()
                if not link_text or link_text == href or href.endswith(link_text):
                    new_text = f" {href} "
                else:
                    new_text = f" {link_text} ({href}) "
                
                a_tag.replace_with(new_text)

        # Final parsed text
        clean_text = soup.get_text()

        if clean_text:
            # Normalization
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in clean_text.splitlines()]
            clean_text = "\n".join(line for line in lines if line)

        return ParsedHTMLResult(
            clean_text=clean_text if clean_text else None,
            image_urls=image_urls
        )