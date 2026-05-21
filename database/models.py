# DB models and tables


from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, BigInteger, func, Table, Column, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


user_channels = Table(
    "user_channels",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    
    last_summary_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    channels: Mapped[List[Channel]] = relationship(
        "Channel",
        secondary=user_channels,
        back_populates="users"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username=@{self.username}>"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        server_default=func.now()
    )

    users: Mapped[List[User]] = relationship(
        "User",
        secondary=user_channels,
        back_populates="channels"
    )

    posts: Mapped[List[Post]] = relationship(
        "Post", 
        back_populates="channel", 
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Channel @{self.username}>"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    entry_id: Mapped[str] = mapped_column(String(255), nullable=False)
    post_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    image_urls: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    
    is_summarized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        server_default=func.now()
    )

    channel: Mapped[Channel] = relationship(
        "Channel",
        back_populates="posts",
        lazy="raise"
    )

    def __repr__(self) -> str:
        return f"<Post hash={self.post_hash[:8]} summarized={self.is_summarized}>"