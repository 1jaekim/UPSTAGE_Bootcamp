"""progress 영속 (SQLite + SQLAlchemy 2.x). boundary = max(기존, 신규) 단조 증가."""
from __future__ import annotations

import os

from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DB_PATH = os.environ.get("SPO_DB", "sqlite:///./spokeeper.db")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class ProgressRow(Base):
    __tablename__ = "progress"
    # (user_id, book_id) 복합 키
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(String, primary_key=True)
    reading_offset: Mapped[int] = mapped_column(Integer, default=0)
    spoiler_boundary: Mapped[int] = mapped_column(Integer, default=0)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_progress(user_id: str, book_id: str) -> ProgressRow:
    with Session(engine) as s:
        row = s.get(ProgressRow, (user_id, book_id))
        if row is None:
            row = ProgressRow(user_id=user_id, book_id=book_id, reading_offset=0, spoiler_boundary=0)
            s.add(row)
            s.commit()
            s.refresh(row)
        return row


def put_progress(user_id: str, book_id: str, reading_offset: int) -> ProgressRow:
    with Session(engine) as s:
        row = s.get(ProgressRow, (user_id, book_id))
        if row is None:
            row = ProgressRow(user_id=user_id, book_id=book_id,
                              reading_offset=0, spoiler_boundary=0)
            s.add(row)
        prev_boundary = row.spoiler_boundary or 0
        row.reading_offset = reading_offset
        # 단조 증가 (SPEC progress 규칙 / 불변 규칙 5)
        row.spoiler_boundary = max(prev_boundary, reading_offset)
        s.commit()
        s.refresh(row)
        return row


def seed_demo_progress(user_id: str = "local", book_id: str = "b_mist", offset: int = 380) -> None:
    """데모 기본값: reading_offset=380 (스크린샷과 일치)."""
    with Session(engine) as s:
        row = s.get(ProgressRow, (user_id, book_id))
        if row is None:
            s.add(ProgressRow(user_id=user_id, book_id=book_id,
                              reading_offset=offset, spoiler_boundary=offset))
            s.commit()
