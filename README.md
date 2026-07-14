# SpoKeeper

> **Your reading position is the spoiler boundary.**

SpoKeeper is an AI-assisted EPUB reader that shows character relationships and contextual reminders using only the part of a book the reader has already reached.

Most summarization and retrieval systems can access an entire book, which makes accidental spoilers difficult to prevent. SpoKeeper instead treats the reader's EPUB CFI and canonical paragraph index as an access boundary. Information beyond that boundary is filtered on the server before it reaches the UI.

## What SpoKeeper Provides

- An EPUB reader powered by epub.js
- Page-based progress display across the reader, graph, reminder panel, and footer
- CFI and `global_index` based spoiler enforcement
- An interactive character relationship graph with full-screen mode and character details
- Context reminders generated only from already revealed information
- EPUB upload, SHA-256 deduplication, CFI indexing, and background analysis
- Persistent reading progress and EPUB-to-`book_id` mapping
- Local snapshots for isolated result validation and Supabase-backed snapshots for shared environments
- Character alias consolidation, relationship summaries, and indirect spoiler checks

## Spoiler-Safety Model

The page number shown in the UI is a derived display value. It may change when the font size, viewport, or EPUB layout changes. It is not used as the security boundary.

```text
epub.js current CFI
        │
        ▼
normalized EPUB CFI
        │
        ▼
book_cfi_index global_index
        │
        ├── progress persistence
        ├── graph snapshot lookup
        ├── relationship filtering
        └── reminder filtering

UI pagination
        └── current page / total pages (display only)
```

The backend selects the latest precomputed snapshot whose boundary is less than or equal to the reader's current `global_index`. Verification and response-time guards remove entities, relationships, events, and reminders that are not safe at that position.

## Main Features

### EPUB Reading and Page Synchronization

- Paginated EPUB rendering with epub.js
- Previous/next page navigation and progress controls
- CFI-based location restoration after refresh
- Page recalculation after viewport reflow
- A consistent page number across the reader, relationship panel, reminder panel, and progress footer
- `Page calculation in progress` fallback while pagination is being generated

### Character Relationship Graph

- Cytoscape-based interactive graph
- Character names displayed directly on nodes
- Curved relationship edges with persistent labels
- Character-specific deterministic colors
- Selection, hover, connected-node emphasis, and detail panels
- Relationship descriptions, aliases, and first-seen information
- Shared presentation rules between the embedded and full-screen graph

### Spoiler-Safe AI Pipeline

The analysis pipeline incrementally processes the book and builds cumulative snapshots:

1. EPUB parser
2. Chunk generator
3. Incremental BuildAgent
4. Character consolidation and alias resolution
5. VerifierAgent
6. ReminderWriterAgent
7. IndirectLeakageJudge
8. Snapshot persistence

New analyses store a snapshot at every analyzed chunk boundary so relationship information can appear progressively instead of being released in large batches.

### Book Upload and Persistence

Uploaded books follow this flow:

```text
EPUB upload
  → SHA-256 duplicate check
  → book_id creation or reuse
  → local EPUB storage
  → relative storage_path persistence
  → CFI index generation
  → immediate reading availability
  → background AI snapshot generation
```

Absolute EPUB paths are never persisted. Paths are resolved relative to `backend/data` and checked against path traversal before use.

## Architecture

```text
frontend/                    React reader and graph UI
    │
    │ HTTP /api
    ▼
backend/app/main.py          FastAPI routes and reading-state contract
    ├── cfi_db.py            CFI ↔ global_index lookup
    ├── book_repository.py   Safe EPUB path and local metadata registry
    ├── content_source.py    Snapshot selection and spoiler filtering
    ├── precompute.py        Incremental snapshot generation
    └── db.py                Local reading-progress persistence
    │
    ├── backend/data/precomputed/*.json
    ├── backend/data/uploaded_books/*.epub
    └── Supabase PostgreSQL
            ├── books
            ├── book_cfi_index
            └── build_agent_snapshots

agents/
    ├── build_agent.py
    ├── verifier_agent.py
    ├── reminder_writer_agent.py
    ├── indirect_leakage_judge.py
    └── consolidation_agent.py
```

## Technology Stack

### Frontend

- React 19
- TypeScript
- Vite
- Zustand
- TanStack Query
- epub.js
- Cytoscape.js and fCoSE
- Tailwind CSS

### Backend and AI

- Python
- FastAPI
- Pydantic
- SQLAlchemy and SQLite for local reading progress
- PostgreSQL / Supabase for book metadata, CFI indexes, and snapshots
- EbookLib and Beautiful Soup
- Upstage Solar through `langchain-upstage`

## Repository Structure

```text
.
├── frontend/
│   ├── src/api/                    API client, contracts, and query hooks
│   ├── src/components/             Reader, panels, and graph UI
│   ├── src/store.ts                Client reading and UI state
│   └── vite.config.ts              /api proxy to FastAPI
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI application
│   │   ├── schemas.py              API schemas
│   │   ├── cfi_db.py               CFI/global-index repository
│   │   ├── book_repository.py      Safe EPUB registry and resolver
│   │   ├── content_source.py       Snapshot sources and spoiler gating
│   │   ├── precompute.py           AI snapshot pipeline
│   │   └── upload_pipeline.py      EPUB ingestion and CFI indexing
│   ├── cfi_tools/                  Node-based EPUB CFI index builder
│   ├── data/                       EPUB files and local snapshot data
│   └── tests/
└── agents/                         Extraction, verification, and reminder agents
```

Run Python commands from the repository root because imports use `backend.*` and `agents.*` from that location.

## Prerequisites

- Python 3.11 or later
- Node.js and npm
- A PostgreSQL/Supabase database for shared book and snapshot data
- An Upstage API key to analyze new books

The frontend mock mode and previously generated local snapshots can be used without running the paid AI analysis pipeline. The live backend still requires the metadata and CFI data needed by the selected book.

## Installation

### 1. Create a Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
```

### 2. Install Node dependencies

```bash
npm install --prefix frontend
npm install --prefix backend/cfi_tools
```

### 3. Configure the backend

Create `backend/.env`:

```dotenv
SUPABASE_DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
UPSTAGE_API_KEY=your_upstage_api_key

# fixture | local | agent
SPO_SOURCE=agent

# Initial book loaded by the backend fixture compatibility layer
SPO_BOOK_ID=your_default_book_id

# development enables the single-EPUB fallback in the safe path resolver
SPO_ENV=development

# Optional analysis granularity (defaults shown)
SPO_CHUNK_SIZE=600
SPO_CHUNK_OVERLAP=100
```

Content source modes:

| Mode | Behavior |
|---|---|
| `fixture` | Uses built-in demonstration data. |
| `local` | Reads `backend/data/precomputed/*.json` without querying Supabase snapshots. |
| `agent` | Loads Supabase snapshots first and falls back to local precomputed files for missing entries. |

### 4. Configure the frontend

Create `frontend/.env`:

```dotenv
VITE_USE_MOCK=false

# Optional. Leave unset to use the Vite /api proxy.
# VITE_API_BASE=http://127.0.0.1:8000
```

## Running the Application

Start the backend from the repository root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open:

- Frontend: <http://localhost:5173>
- Backend health check: <http://127.0.0.1:8000/api/health>
- OpenAPI documentation: <http://127.0.0.1:8000/docs>

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend health check |
| `GET` | `/api/books` | List available books |
| `POST` | `/api/books/upload` | Upload, index, and schedule analysis for an EPUB |
| `GET` | `/api/books/{book_id}` | Get book metadata and chapter indexes |
| `DELETE` | `/api/books/{book_id}` | Delete a book and its local files |
| `GET` | `/api/books/{book_id}/file` | Stream the EPUB to epub.js |
| `GET` | `/api/books/{book_id}/chapters/{index}` | Get parsed chapter content |
| `GET` | `/api/books/{book_id}/graph` | Get the spoiler-safe relationship graph |
| `GET` | `/api/books/{book_id}/reminders` | Get spoiler-safe contextual reminders |
| `GET` | `/api/books/{book_id}/progress` | Read persisted progress |
| `PUT` | `/api/books/{book_id}/progress` | Save CFI, global index, and page metadata |
| `GET` | `/api/books/{book_id}/analysis-status` | Poll background analysis progress |

Graph and reminder requests accept `current_global_index`, `current_page`, and `total_pages`. The backend uses `current_global_index` for filtering and returns page values only as presentation metadata.

## Local EPUB and Snapshot Storage

- Uploaded EPUBs: `backend/data/uploaded_books/{book_id}.epub`
- Local metadata registry: `backend/data/book_registry.json`
- Local snapshots: `backend/data/precomputed/{book_id}.json`
- Local progress database: `spokeeper.db`

EPUBs placed directly under `backend/data` are discovered at backend startup and receive a deterministic ID based on their SHA-256 hash. For full CFI indexing and AI analysis, use the upload API or run the analysis pipeline explicitly.

Existing snapshots keep the granularity with which they were originally generated. Re-run analysis to apply newer per-chunk snapshot behavior to an older book.

## Validation

Backend tests:

```bash
python -m pytest backend/tests -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

CFI mapping and spoiler-boundary behavior have dedicated regression tests under `backend/tests`.

## Design Principles

1. **The server owns spoiler enforcement.** Future data is filtered before the API response is created.
2. **CFI/global index is authoritative.** Page numbers are presentation-only derived values.
3. **Progress and spoiler boundaries are separate.** The current location can move backward while the normal spoiler boundary remains monotonic unless the user explicitly resets it.
4. **Stored paths are relative and validated.** EPUB resolution cannot escape `backend/data`.
5. **Existing API contracts remain backward compatible.** Legacy offset fields are retained while CFI, global-index, and page metadata are added.
