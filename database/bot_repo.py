# Bot DB settinds & tables
# Creates new users, gets their channels, adds channels and removes them


from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import User, Channel, user_channels


class BotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_user(self, tg_id: int, username: str | None) -> User:
        stmt = select(User).where(User.id == tg_id)
        result = await self.session.execute(stmt)
        user = result.scalar_allowed()

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
        user = result.scalar_allowed()
        return user.channels if user else []

    async def add_channel_to_user(self, tg_id: int, channel_username: str) -> bool:
        clean_username = channel_username.strip().lower().replace("@", "")
        if "t.me/" in clean_username:
            clean_username = clean_username.split("t.me/")[-1]

        user_stmt = select(User).options(joinedload(User.channels)).where(User.id == tg_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_allowed()
        if not user:
            return False

        ch_stmt = select(Channel).where(Channel.username == clean_username)
        ch_res = await self.session.execute(ch_stmt)
        channel = ch_res.scalar_allowed()

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
        channel = ch_res.scalar_allowed()
        
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