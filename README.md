<p align="right">
  <a href="./README_EN.md">🇺🇸 English</a>
</p>

# 🍀 SpoKeeper

> **"읽기 위치가 스포일러의 경계가 됩니다."**

SpoKeeper는 사용자가 현재까지 읽은 소설의 내용만을 기반으로 **인물 관계도(Context Graph)** 와 **맥락 리마인드(Context Reminder)** 를 제공하는 AI 기반 **Spoiler-Safe 독서 보조 서비스**입니다.

기존 AI 요약 서비스나 RAG 기반 검색은 책 전체를 참조하기 때문에 의도치 않은 스포일러가 발생할 수 있습니다.

SpoKeeper는 **현재 읽기 위치(Offset)** 를 기준으로 정보 접근을 제한하고, **Multi-Agent Workflow**를 통해 미래 내용을 차단하면서 독서 경험을 돕는 것을 목표로 합니다.

---

# 프로젝트 개요

사용자는 EPUB 소설을 업로드한 후 평소처럼 책을 읽기만 하면 됩니다.

SpoKeeper는 사용자의 현재 읽기 위치까지 등장한

- 등장인물
- 인물 관계
- 주요 사건

을 자동으로 분석하고,

현재까지의 내용을 기반으로

- 인물 관계도
- Context Reminder

를 제공합니다.

---

#  해결하려는 문제

독서 중 AI를 활용할 때 가장 큰 문제는 **스포일러**입니다.

| 문제 | 설명 |
|------|------|
| 스포일러 발생 | AI가 미래 사건이나 등장인물을 함께 설명하는 문제 |
| 등장인물 기억 어려움 | 장편 소설일수록 인물 관계를 기억하기 어려움 |
| 줄거리 기억 부족 | 오랜만에 다시 읽으면 앞 내용을 잊어버림 |

SpoKeeper는 **"현재 읽은 위치까지만"** 정보를 제공하여 이러한 문제를 해결합니다.

---

#  핵심 기능

###  EPUB Parser : EPUB 파일에서 본문과 챕터를 자동 추출합니다.

###  AI BuildAgent : 등장인물, 관계, 사건을 자동 분석합니다.

###  Knowledge Graph : 현재까지 등장한 인물 관계를 시각화합니다.

###  Context Reminder : 현재 읽은 위치까지의 내용을 자연스럽게 요약합니다.

###  Spoiler Guard : Offset 기반으로 미래 내용을 차단하여 스포일러를 방지합니다.

---

## 1️ VerifierAgent (1차 Guard)

Retriever가 검색한 결과 중

```
정보 Offset ≤ 사용자 Offset
```

인 정보만 통과시킵니다.

---

## 2️ ReminderWriterAgent

현재 Offset 이하의 정보만 이용하여

리마인드를 생성합니다.

추측, 해석, 미래 예측은 수행하지 않습니다.

---

## 3️ Render Guard (예정)

생성된 결과를 다시 Offset 기준으로 검증하여

미래 정보가 포함되지 않았는지 확인합니다.

---

## 4️ IndirectLeakageJudge (예정)

직접적인 스포일러뿐 아니라

- 암시
- 복선
- 미래를 연상시키는 표현

까지 판단하여

- PASS
- REWRITE
- SUPPRESS

중 하나를 선택합니다.

---

#  Agent Workflow

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

 Avatar Prompt (예정)

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

 IndirectLeakageJudge (예정)

              │

              ▼

      Render Guard (예정)

              │

              ▼

            사용자
```

---

#  프로젝트 구조

저장소는 **frontend / backend / agents** 3개 폴더로 구성된다.

```text
.
├── frontend/                # React + Vite (읽기 UI, 관계도, 리마인드)
│   ├── src/
│   │   ├── api/             # 통합 계약 타입·클라이언트·훅
│   │   └── components/
│   └── vite.config.ts       # /api → 127.0.0.1:8000 프록시
│
├── backend/                 # FastAPI 서빙 (계약 graph_json·reminders·progress)
│   ├── app/
│   │   ├── main.py          # 라우트 + 소스 주입(_make_source)
│   │   ├── schemas.py       # 통합 계약 스키마
│   │   ├── content_source.py# FixtureSource / AgentResultSource
│   │   ├── agent_adapter.py # 에이전트 출력 → 계약 변환
│   │   ├── precompute.py    # 경계선별 build 결과 → 계약 JSON store
│   │   └── db.py, fixtures.py
│   ├── scripts/make_demo_store.py
│   └── tests/
│
└── agents/                  # AI 에이전트 파이프라인 (Solar-Pro2 + LangChain)
    ├── build_agent.py       # 인물·관계·사건 추출 (+ 증분 빌드)
    ├── character_profiler_agent.py
    ├── parsers/epub_parser.py
    ├── tools/chunk_tool.py
    ├── config.py
    ├── app.py               # Streamlit 프로토타입
    ├── data/books/          # EPUB 샘플
    └── requirements.txt
```

> 실행: 모든 명령은 **저장소 최상위**에서. `agents`·`backend` 는 최상위를 sys.path 기준으로
> import 한다 (`from agents.build_agent import ...`, `from backend.app...`).

---

#  기술 스택

### AI

- Upstage Solar-Pro2
- LangChain

### Vector Database

- ChromaDB

### Backend

- Python
- Streamlit (Prototype)

### 예정

- FastAPI
- React

---





#  개발 진행 현황

| 기능 | 상태 |
|------|------|
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

#  기대 효과

###  독자

- 등장인물 관계를 쉽게 이해
- 줄거리 기억 부담 감소
- 스포일러 없는 독서 경험

###  AI 서비스

- Offset 기반 접근 제어
- Multi-Agent Workflow
- Knowledge Graph 기반 관계 관리
- Spoiler Guard 구조를 통한 안전한 AI 독서 지원

---
