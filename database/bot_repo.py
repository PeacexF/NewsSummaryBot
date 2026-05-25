# Bot DB settinds & tables
# Creates new users, gets their channels, adds channels and removes them


from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import User, Channel, user_channels
from database.crypto import encrypt_key, decrypt_key


class BotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_user(self, tg_id: int, username: str | None) -> User:
        stmt = select(User).where(User.id == tg_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(id=tg_id, username=username)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        elif user.username != username:
            user.username = username
            await self.session.commit()
            
        return user

    async def get_user_channels(self, tg_id: int) -> list[Channel]:
        stmt = (
            select(User)
            .options(joinedload(User.channels))
            .where(User.id == tg_id)
        )
        result = await self.session.execute(stmt)
        user = result.unique().scalar_one_or_none()
        return user.channels if user else []

    async def add_channel_to_user(self, tg_id: int, channel_username: str) -> bool:
        clean_username = channel_username.strip().lower().replace("@", "")
        if "t.me/" in clean_username:
            clean_username = clean_username.split("t.me/")[-1]

        user_stmt = select(User).options(joinedload(User.channels)).where(User.id == tg_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.unique().scalar_one_or_none()
        if not user:
            return False

        ch_stmt = select(Channel).where(Channel.username == clean_username)
        ch_res = await self.session.execute(ch_stmt)
        channel = ch_res.scalar_one_or_none()

        if not channel:
            channel = Channel(username=clean_username, title=clean_username)
            self.session.add(channel)
            await self.session.flush() # get new chanel id witout a full commit

        if channel in user.channels:
            return False

        user.channels.append(channel)
        await self.session.commit()
        return True

    async def remove_channel_from_user(self, tg_id: int, channel_username: str) -> bool:
        ch_stmt = select(Channel).where(Channel.username == channel_username)
        ch_res = await self.session.execute(ch_stmt)
        channel = ch_res.scalar_one_or_none()
        
        if not channel:
            return False

        stmt = (
            delete(user_channels)
            .where(user_channels.c.user_id == tg_id)
            .where(user_channels.c.channel_id == channel.id)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_user_api_key(self, tg_id: int, plain_key: str) -> bool:
        stmt = select(User).where(User.id == tg_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.gemini_api_key = encrypt_key(plain_key)
        await self.session.commit()
        return True

    async def delete_user_api_key(self, tg_id: int) -> bool:
        stmt = select(User).where(User.id == tg_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.gemini_api_key:
            return False
            
        user.gemini_api_key = None
        await self.session.commit()
        return True

    async def get_user_api_key(self, tg_id: int) -> str | None:
        stmt = select(User).where(User.id == tg_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.gemini_api_key:
            return None
            
        return decrypt_key(user.gemini_api_key)