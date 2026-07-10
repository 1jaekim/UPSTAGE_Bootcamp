"""FastAPI 서빙 (SPEC §3). 계약(graph_json·reminders)을 그대로 서빙한다.

소스는 ContentSource 뒤에 추상화되어 있어, 초기 FixtureSource → B2에서 AgentResultSource
로 '주입만' 교체한다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import cfi_db, db, fixtures as fx
from .content_source import ContentSource
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
from .source_factory import make_content_source


# ── 소스 주입 (교체 지점) ────────────────────────────────────────
# SPO_SOURCE=agent: Supabase(build_agent_snapshots)를 우선 사용하고, 없는 key만
# backend/data/precomputed/*.json으로 보충한다.
# SPO_SOURCE=local: 테스트/개발 검증 전용. Supabase를 전혀 조회하지 않고 로컬
# precomputed JSON만 사용한다.
content_source: ContentSource = make_content_source()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    db.seed_demo_progress()  # 데모 기본 reading_offset/spoiler_boundary(global_index)=380
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


@app.get("/api/books/{book_id}/file")
def get_book_file(book_id: str):
    """epub.js가 브라우저에서 직접 렌더링할 수 있도록 원본 EPUB 바이트를 서빙한다."""
    _require_book(book_id)
    path = Path(fx._epub_path_for(book_id))
    if not path.exists():
        raise HTTPException(status_code=404, detail="원본 EPUB 파일을 찾을 수 없습니다.")
    return FileResponse(path, media_type="application/epub+zip", filename=path.name)


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
    # API 호환을 위해 query parameter 이름은 offset이지만, 값의 의미는
    # book_cfi_index 기준 spoiler boundary global_index다.
    boundary_global_index = offset
    return content_source.get_graph(book_id, boundary_global_index, reveal_all)


@app.get("/api/books/{book_id}/reminders", response_model=Reminders)
def get_reminders(
    book_id: str,
    offset: int = Query(..., ge=0),
    entity_id: str | None = Query(None),
) -> Reminders:
    _require_book(book_id)
    # API 호환을 위해 query parameter 이름은 offset이지만, 값의 의미는
    # book_cfi_index 기준 spoiler boundary global_index다.
    boundary_global_index = offset
    return content_source.get_reminders(book_id, boundary_global_index, entity_id)


@app.get("/api/books/{book_id}/progress", response_model=Progress)
def get_progress(book_id: str, user_id: str = "local") -> Progress:
    _require_book(book_id)
    row = db.get_progress(user_id, book_id)
    reading_global_index = row.reading_offset
    spoiler_boundary_global_index = row.spoiler_boundary
    cfi = (
        cfi_db.cfi_for_global_index(book_id, reading_global_index)
        if reading_global_index
        else None
    )
    return Progress(
        user_id=row.user_id,
        book_id=row.book_id,
        # 응답 필드명은 기존 계약을 유지하지만 둘 다 book_cfi_index global_index다.
        reading_offset=reading_global_index,
        spoiler_boundary=spoiler_boundary_global_index,
        cfi=cfi,
    )


@app.put("/api/books/{book_id}/progress", response_model=Progress)
def put_progress(book_id: str, body: ProgressUpdate) -> Progress:
    _require_book(book_id)
    reading_global_index = (
        cfi_db.find_global_index_by_cfi(book_id, body.cfi)
        if body.cfi
        else body.reading_offset
    )
    row = db.put_progress(
        body.user_id,
        book_id,
        reading_global_index,
        force=body.force,
    )
    stored_reading_global_index = row.reading_offset
    stored_spoiler_boundary_global_index = row.spoiler_boundary
    cfi = (
        cfi_db.cfi_for_global_index(book_id, stored_reading_global_index)
        if stored_reading_global_index
        else None
    )
    return Progress(
        user_id=row.user_id,
        book_id=row.book_id,
        # 응답 필드명은 기존 계약을 유지하지만 둘 다 book_cfi_index global_index다.
        reading_offset=stored_reading_global_index,
        spoiler_boundary=stored_spoiler_boundary_global_index,
        cfi=cfi,
    )


def _run_full_analysis(book_id: str) -> None:
    """BuildAgent~IndirectLeakageJudge 4단계 파이프라인을 백그라운드에서 실행.

    업로드 응답은 CFI 인덱싱만 끝나면 바로 나가고, 이 분석(몇 분~수십 분 소요, LLM
    호출 다수)은 별도로 돌아간다. 완료되면 precompute_from_epub이 알아서
    Supabase build_agent_snapshots에 적재하므로, 다음 요청부터 바로 서빙된다.
    """
    from agents.parsers.epub_parser import parse_epub
    from agents.tools.chunk_tool import make_chunks
    from .precompute import precompute_from_epub
    from .upload_pipeline import epub_path_for

    epub_path = str(epub_path_for(book_id))
    parsed = parse_epub(epub_path)
    chunks = make_chunks(parsed["chapters"])
    last = len(chunks) - 1
    boundaries = list(range(4, last, 5)) + [last]

    try:
        precompute_from_epub(epub_path, book_id, boundaries)
    except Exception as e:  # pragma: no cover - 백그라운드 작업 실패는 로그만
        print(f"[분석 실패] book_id={book_id}: {e}")


@app.post("/api/books/upload")
async def upload_book(file: UploadFile, background_tasks: BackgroundTasks) -> dict:
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="EPUB 파일만 업로드할 수 있습니다.")

    epub_bytes = await file.read()
    title = Path(file.filename).stem

    try:
        result = ingest_epub(epub_bytes, file.filename, title)
    except CfiBuildError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if not result["reused"]:
        background_tasks.add_task(_run_full_analysis, result["book_id"])

    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
