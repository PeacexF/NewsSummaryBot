# Deduplication is done at the Storage Layer
# But it only filters the exact same posts via hash
# The problem is that most tgc just rephrase the same stuff (or just repost)
# Therefore we need to filter them in order to not get bankrupt from the token usage and to save water from the data canters xd

# So this module:
# Does a request to DB -> Shingle's Algorithm aka (MinHash / Jaccard Similarity) (links below) -> send formatted text to AI -> (maybe store a raw deduplicated version too)
# https://nlp.stanford.edu/IR-book/html/htmledition/near-duplicates-and-shingling-1.html 
# https://en.wikipedia.org/wiki/W-shingling
# https://blog.nelhage.com/post/fuzzy-dedup/


from __future__ import annotations

import re

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Post, Channel
from client.rss import RSSItem


class NewsFilter:
    def __init__(self, similarity_threshold: float = 0.6, shingle_size: int = 2) -> None:
        self.threshold = similarity_threshold   # from 0.0 to 1.0, > 0.6 = duplicate
        self.shingle_size = shingle_size

    async def get_fresh_posts(self, session: AsyncSession) -> list[Post]:
        time_threshold = datetime.now(timezone.utc) - timedelta(days=1)
        
        stmt = (
            select(Post)
            .join(Post.channel)
            .options(joinedload(Post.channel))
            .where(Post.is_summarized == False)
            .where(Post.published_at >= time_threshold)
            .where(Channel.is_active == True)
            .order_by(Post.published_at.asc())
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _get_shingles(self, text: str) -> set[str]:
        # Normalize text and get shingles
        # Note: links are only remoevd in the INNER text used to calculate shingles, as links ruin them
        clean_text = re.sub(r"\(https?://[^\)]+\)", "", text)
        words = re.sub(r"[^\w\s]", "", clean_text.lower()).split()
        
        if len(words) <= self.shingle_size:
            return set(words)
            
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i : i + self.shingle_size])
            shingles.add(shingle)
        return shingles

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        # Calculates the similarity coef
        if not set1 or not set2:
            return 0.0
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union)

    def filter_duplicates(self, posts: list[Post]) -> list[Post]:
        # Removes duplicate posts
        if not posts:
            return []

        unique_posts: list[Post] = []
        # storing already calculated shingles for optimization
        computed_shingles: list[set[str]] = []

        for post in posts:
            if not post.text:
                continue
                
            current_shingles = self._get_shingles(post.text)
            is_duplicate = False

            for existing_shingles in computed_shingles:
                similarity = self._jaccard_similarity(current_shingles, existing_shingles)
                if similarity >= self.threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_posts.append(post)
                computed_shingles.append(current_shingles)

        return unique_posts

    def format_for_ai(self, filtered_posts: list[Post]) -> str:
        # Packs into XML
        formatted_blocks = []
        for _, post in enumerate(filtered_posts, 1):
            block = (
                f"<post id='{post.id}'>\n"
                f"<source>@{post.channel.username}</source>\n"
                f"<text>{post.text}</text>\n"
                f"</post>"
            )
            formatted_blocks.append(block)
        return "\n\n".join(formatted_blocks)