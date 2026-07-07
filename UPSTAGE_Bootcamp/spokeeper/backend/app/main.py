"""FastAPI 서빙 (SPEC §3). 계약(graph_json·reminders)을 그대로 서빙한다.

소스는 ContentSource 뒤에 추상화되어 있어, 초기 FixtureSource → B2에서 AgentResultSource
로 '주입만' 교체한다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import db, fixtures as fx
from .content_source import ContentSource, FixtureSource
from .schemas import (
    Book,
    BookSummary,
    Chapter,
    GraphJson,
    Progress,
    ProgressUpdate,
    Reminders,
)

# ── 소스 주입 (교체 지점) ────────────────────────────────────────
content_source: ContentSource = FixtureSource()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    db.seed_demo_progress()  # 데모 기본 offset=380
    yield


app = FastAPI(title="SpoKeeper Serving", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 데모: 로컬 프론트 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

_BOOKS = {fx.BOOK_MIST.id: fx.BOOK_MIST}


def _require_book(book_id: str) -> Book:
    book = _BOOKS.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} 없음")
    return book


@app.get("/api/books", response_model=list[BookSummary])
def list_books() -> list[BookSummary]:
    return [
        BookSummary(id=b.id, title=b.title, author=b.author, total_offset=b.total_offset)
        for b in _BOOKS.values()
    ]


@app.get("/api/books/{book_id}", response_model=Book)
def get_book(book_id: str) -> Book:
    return _require_book(book_id)


@app.get("/api/books/{book_id}/chapters/{index}", response_model=Chapter)
def get_chapter(book_id: str, index: int) -> Chapter:
    _require_book(book_id)
    if index not in fx.CHAPTER_CONTENT:
        raise HTTPException(status_code=404, detail=f"chapter {index} 없음")
    return fx.chapter_with_content(index)


@app.get("/api/books/{book_id}/graph", response_model=GraphJson)
def get_graph(
    book_id: str,
    offset: int = Query(..., ge=0),
    reveal_all: bool = Query(False),
) -> GraphJson:
    _require_book(book_id)
    return content_source.get_graph(book_id, offset, reveal_all)


@app.get("/api/books/{book_id}/reminders", response_model=Reminders)
def get_reminders(
    book_id: str,
    offset: int = Query(..., ge=0),
    entity_id: str | None = Query(None),
) -> Reminders:
    _require_book(book_id)
    return content_source.get_reminders(book_id, offset, entity_id)


@app.get("/api/books/{book_id}/progress", response_model=Progress)
def get_progress(book_id: str, user_id: str = "local") -> Progress:
    _require_book(book_id)
    row = db.get_progress(user_id, book_id)
    return Progress(user_id=row.user_id, book_id=row.book_id,
                    reading_offset=row.reading_offset, spoiler_boundary=row.spoiler_boundary)


@app.put("/api/books/{book_id}/progress", response_model=Progress)
def put_progress(book_id: str, body: ProgressUpdate) -> Progress:
    _require_book(book_id)
    row = db.put_progress(body.user_id, book_id, body.reading_offset)
    return Progress(user_id=row.user_id, book_id=row.book_id,
                    reading_offset=row.reading_offset, spoiler_boundary=row.spoiler_boundary)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
