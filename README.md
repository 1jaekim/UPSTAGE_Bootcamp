# 🍀 SpoKeeper

> **"Your reading position becomes the boundary against spoilers."**

SpoKeeper is an AI-powered **Spoiler-Safe Reading Assistant** that provides a **Character Relationship Graph (Context Graph)** and **Context Reminder** based only on the content of a novel that the user has read so far.

Existing AI summarization services and RAG-based search systems may reference the entire book, which can unintentionally expose users to spoilers.

SpoKeeper aims to enhance the reading experience while preventing access to future content by restricting information based on the user's **current reading position (Offset)** and using a **Multi-Agent Workflow**.

---

# Project Overview

Users simply upload an EPUB novel and read it as usual.

SpoKeeper automatically analyzes the following information that has appeared up to the user's current reading position:

- Characters
- Character relationships
- Major events

Based only on the content read so far, it provides:

- Character Relationship Graph
- Context Reminder

---

# Problems We Aim to Solve

The biggest challenge when using AI while reading is **spoilers**.

| Problem | Description |
|---|---|
| Spoiler Exposure | AI may reveal future events or characters |
| Difficulty Remembering Characters | The longer the novel, the harder it becomes to remember character relationships |
| Difficulty Remembering the Story | Readers may forget previous events when returning to a book after a long break |

SpoKeeper solves these problems by providing information **"only up to the user's current reading position."**

---

# Core Features

### EPUB Parser

Automatically extracts text and chapters from EPUB files.

### AI BuildAgent

Automatically analyzes characters, relationships, and events.

### Knowledge Graph

Visualizes character relationships that have appeared up to the current reading position.

### Context Reminder

Naturally summarizes the story up to the user's current reading position.

### Spoiler Guard

Prevents spoilers by blocking future information based on the user's Offset.

---

## 1. VerifierAgent (First Guard)

Among the results retrieved by the RetrieverAgent, only information satisfying the following condition is allowed to pass:

```text
Information Offset ≤ User Offset
```

---

## 2. ReminderWriterAgent

Generates reminders using only information with an Offset less than or equal to the user's current Offset.

It does not perform speculation, interpretation, or prediction of future events.

---

## 3. Render Guard (Planned)

Revalidates the generated output based on the Offset to ensure that no future information is included.

---

## 4. IndirectLeakageJudge (Planned)

Evaluates not only direct spoilers but also:

- Hints
- Foreshadowing
- Expressions that may imply future events

It then selects one of the following actions:

- PASS
- REWRITE
- SUPPRESS

---

# Agent Workflow

```text
                 EPUB

                   │

             ParserAgent

                   │

             ChunkAgent

                   │

              ChromaDB

                   │

      Incremental BuildAgent

                   │

             BuildAgent

                   │

         Knowledge Graph

        ┌──────────┴──────────┐

        ▼                     ▼

 CharacterProfiler      Graph Viewer

        │

        ▼

 Avatar Prompt (Planned)

────────────────────────────────────

       RetrieverAgent

              │

              ▼

      VerifierAgent

              │

              ▼

    ReminderWriterAgent

              │

              ▼

 IndirectLeakageJudge (Planned)

              │

              ▼

      Render Guard (Planned)

              │

              ▼

             User
```

---

# Project Structure

The repository is organized into three main directories: **frontend / backend / agents**.

```text
.
├── frontend/                # React + Vite (Reader UI, relationship graph, reminders)
│   ├── src/
│   │   ├── api/             # Unified contract types, clients, and hooks
│   │   └── components/
│   └── vite.config.ts       # /api → 127.0.0.1:8000 proxy
│
├── backend/                 # FastAPI serving layer (graph_json, reminders, progress contracts)
│   ├── app/
│   │   ├── main.py          # Routes + source injection (_make_source)
│   │   ├── schemas.py       # Unified contract schemas
│   │   ├── content_source.py# FixtureSource / AgentResultSource
│   │   ├── agent_adapter.py # Converts agent output → contract format
│   │   ├── precompute.py    # Build results by boundary → contract JSON store
│   │   └── db.py, fixtures.py
│   ├── scripts/make_demo_store.py
│   └── tests/
│
└── agents/                  # AI agent pipeline (Solar-Pro2 + LangChain)
    ├── build_agent.py       # Character, relationship, and event extraction (+ incremental build)
    ├── character_profiler_agent.py
    ├── parsers/epub_parser.py
    ├── tools/chunk_tool.py
    ├── config.py
    ├── app.py               # Streamlit prototype
    ├── data/books/          # EPUB samples
    └── requirements.txt
```

> Execution: Run all commands from the **repository root**. Both `agents` and `backend` use the repository root as the `sys.path` base for imports (`from agents.build_agent import ...`, `from backend.app...`).

---

# Tech Stack

### AI

- Upstage Solar-Pro2
- LangChain

### Vector Database

- ChromaDB

### Backend

- Python
- Streamlit (Prototype)

### Planned

- FastAPI
- React

---

# Development Status

| Feature | Status |
|---|---|
| EPUB Parser | ✅ |
| Chunk Generator | ✅ |
| ChromaDB | ✅ |
| Incremental BuildAgent | ✅ |
| BuildAgent | ✅ |
| CharacterProfilerAgent | ✅ |
| Graph Viewer | ✅ |
| VerifierAgent | ✅ |
| ReminderWriterAgent | 🚧 |
| Render Guard | 🚧 |
| IndirectLeakageJudge | 🚧 |
| AvatarGeneratorAgent | 🚧 |

---

# Expected Benefits

### Readers

- Easily understand character relationships
- Reduce the burden of remembering the storyline
- Enjoy a spoiler-free reading experience

### AI Services

- Offset-based access control
- Multi-Agent Workflow
- Knowledge Graph-based relationship management
- Safe AI-assisted reading through a Spoiler Guard architecture

---

<details>
<summary><b>🇰🇷 한국어 보기</b></summary>

<br>

# 🍀 SpoKeeper

> **"읽기 위치가 스포일러의 경계가 됩니다."**

여기에 기존 한국어 README 전체 내용을 그대로 붙여넣기

</details>
