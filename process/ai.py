# This module takes the XML output from filter and creates an ai generated summary based on the provided list of posts.

# Prompt can be seen in assets/prompt.md
# I will try to implement batch requests in order to save more on API costs
# Also wanna add support for more LLM models to maybe just switch free trials for personal use
# But will need to add a feature to add an API key from the bot itself, would be actually cool though (just shouldn't log them anywhere lmao)
# Practically cutting costs to zero if you just spam accounts and free trials
# Like yeah i'll do it that honestly sounds fire af, bring your own free keys and just simply rotate them with infinite accounts
# The backend here is going to be insane, yeah, but i think it's worth it

# For now i'm only doing Gemini tho and it's already pretty hard to make it work

from __future__ import annotations

import os
import asyncio

from google import genai
from google.genai import types

from log.log import logger


class GeminiSummarizer:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("API key cannot be empty")
            
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.prompt_path = os.path.join("assets", "prompt.md")

    def _load_system_prompt(self) -> str:
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"AI | Failed to load system prompt from {self.prompt_path}: {e}")
            return "Ты — ИИ-ассистент. Сделай краткую выжимку присланных новостей в формате Markdown на русском языке."

    ## THERE IS NO CACHING ON A FREE TARIF FUUUCKKCC
    # async def create_context_cache(self, ttl_seconds: int = 300) -> str | None:
    #     # Caching the prompt for efficiency and economy of input tokens, returns cache id
    #     try:
    #         system_instruction = self._load_system_prompt()
            
    #         cache = await asyncio.to_thread(
    #             self.client.caches.create,
    #             model=self.model_name,
    #             config=types.CreateCachedContentConfig(
    #                 contents=system_instruction,
    #                 ttl=f"{ttl_seconds}s", 
    #                 display_name="news_summary_prompt_cache"
    #             )
    #         )
    #         logger.info(f"AI | Succes caching your fucking prompt of slop. ID: {cache.name}")
    #         return cache.name
    #     except Exception as e:
    #         logger.error(f"AI | Not a Succes caching your fucking prompt of slop: {e}")
    #         return None

    async def generate_chunk_summary(self, xml_chunk: str) -> str | None:
        try:
            system_instruction = self._load_system_prompt()

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.25,
                max_output_tokens=4096
            )

            user_content = f"Вот пачка новостей для обработки:\n\n{xml_chunk}"

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=user_content,
                config=config
            )

            if response and response.text:
                return response.text.strip()
            return None

        except Exception as e:
            logger.error(f"AI | Ошибка при обработке xml: {e}")
            return None