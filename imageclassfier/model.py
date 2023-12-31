from datetime import datetime

from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.utcnow()


class Base(DeclarativeBase):
    ...


class Author(Base):
    __tablename__ = "_author"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(True), default=now, nullable=False
    )
    name: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)
    platform_id: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"Author(id = '{self.id}' , platform_id = '{self.platform_id}' , platform = '{self.platform}' , name = '{self.name}')"


class Platform(Base):
    __tablename__ = "_platform"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(True), default=now, nullable=False
    )
    author_id: Mapped[int] = mapped_column(Integer, comment="作者在数据库中对应的id")
    platform_id: Mapped[int] = mapped_column(Integer)
    platform: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, default="")

    def __repr__(self) -> str:
        return f"Platform(platform_id = '{self.platform_id}' , platform = '{self.platform}' , author_id = '{self.author_id}' , name = '{self.name}')"


import logging
import os
from pathlib import Path

# logging.getLogger("sqlalchemy.engine").setLevel(logging)
# logging.getLogger("sqlalchemy.pool").setLevel(logging)
# logging.getLogger("sqlalchemy.dialects").setLevel(logging)
# logging.getLogger("sqlalchemy.orm").setLevel(logging)

engine = create_engine(
    "sqlite:///database.sqlite",
    # echo=(debug is not None),
    logging_name=None,
    pool_logging_name=None,
)
Base.metadata.create_all(engine)
logging.getLogger().debug(f"Sqlite file locates at {Path('database.sqlite')}.")
