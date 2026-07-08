"""FastAPI 서빙 (SPEC §3). 계약(graph_json·reminders)을 그대로 서빙한다.

소스는 ContentSource 뒤에 추상화되어 있어, 초기 FixtureSource → B2에서 AgentResultSource
로 '주입만' 교체한다.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import cfi_db, db, fixtures as fx
from .content_source import AgentResultSource, ContentSource, FixtureSource
from .precompute import STORE_DIR
from .schemas import (
    Book,
    BookSummary,
    Chapter,
    GraphJson,
    Progress,
    ProgressUpdate,
    Reminders,
)
from .upload_pipeline import CfiBuildError, ingest_epub


# ── 소스 주입 (교체 지점) ────────────────────────────────────────
# SPO_SOURCE=agent 면 precompute 결과(AgentResultSource)를, 아니면 FixtureSource 를 서빙.
# 계약이 동일하므로 라우트/스키마 변경 없이 이 선택만 바뀐다.
# AgentResultSource._store는 (book_id, boundary) 복합키라 원래도 여러 책을 담을 수 있었는데,
# 예전엔 book_id 하나짜리 파일만 로드해서 사실상 단일 책만 서빙되고 있었다 — 이제
# data/precomputed/ 안의 모든 책 precompute 파일을 합쳐서 로드한다.
def _make_source() -> ContentSource:
    if os.environ.get("SPO_SOURCE", "fixture").lower() == "agent":
        combined_store: dict = {}
        for path in sorted(STORE_DIR.glob("*.json")):
            combined_store.update(AgentResultSource.from_json_file(path)._store)
        if combined_store:
            return AgentResultSource(combined_store)
        print(f"[SPO_SOURCE=agent] precompute 파일 없음: {STORE_DIR} → FixtureSource 폴백")
    return FixtureSource()


content_source: ContentSource = _make_source()


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

def _all_books() -> dict[str, Book]:
    books = {fx.BOOK_MIST.id: fx.BOOK_MIST}
    for row in cfi_db.list_books():
        if row["book_id"] in books:
            continue
        books[row["book_id"]] = fx.book_for(row["book_id"], title=row["title"])
    return books


def _require_book(book_id: str) -> Book:
    book = _all_books().get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} 없음")
    return book


@app.get("/api/books", response_model=list[BookSummary])
def list_books() -> list[BookSummary]:
    return [
        BookSummary(id=b.id, title=b.title, author=b.author, total_offset=b.total_offset)
        for b in _all_books().values()
    ]


@app.get("/api/books/{book_id}", response_model=Book)
def get_book(book_id: str) -> Book:
    return _require_book(book_id)


@app.get("/api/books/{book_id}/chapters/{index}", response_model=Chapter)
def get_chapter(book_id: str, index: int) -> Chapter:
    book = _require_book(book_id)
    if index not in {c.index for c in book.chapters}:
        raise HTTPException(status_code=404, detail=f"chapter {index} 없음")
    return fx.chapter_with_content(book_id, index)


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
    row = db.put_progress(body.user_id, book_id, body.reading_offset, force=body.force)
    return Progress(user_id=row.user_id, book_id=row.book_id,
                    reading_offset=row.reading_offset, spoiler_boundary=row.spoiler_boundary)


@app.post("/api/books/upload")
async def upload_book(file: UploadFile) -> dict:
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="EPUB 파일만 업로드할 수 있습니다.")

    epub_bytes = await file.read()
    title = Path(file.filename).stem

    try:
        result = ingest_epub(epub_bytes, file.filename, title)
    except CfiBuildError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
