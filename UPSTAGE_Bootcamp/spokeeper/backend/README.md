# SpoKeeper — Serving Backend (FastAPI)

FE 계약(`graph_json`·`reminders`)을 그대로 서빙. 스포일러 게이팅(strict_chunk_end)은
**서버에서** 수행한다 — 경계선 뒤 데이터는 클라이언트로 보내지 않는다 (불변 규칙 2·6).

## 실행
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000   # spokeeper/ 디렉토리에서 실행
pytest backend/tests -q
```

## 엔드포인트 (SPEC §3)
| 메서드 · 경로 | 설명 |
|---|---|
| `GET /api/books` · `/{id}` | 목록 / 메타·챕터 인덱스 |
| `GET /api/books/{id}/chapters/{index}` | 챕터 본문 |
| `GET /api/books/{id}/graph?offset=&reveal_all=` | 계약 graph_json |
| `GET /api/books/{id}/reminders?offset=&entity_id=` | 계약 reminders |
| `GET·PUT /api/books/{id}/progress` | 진행 조회/갱신 (boundary 단조증가) |

## 소스 추상화 (교체 지점)
`ContentSource` 인터페이스 뒤에 두 구현:
- **`FixtureSource`** (현재) — 정적 시드 픽스처 + strict_chunk_end 게이팅.
- **`AgentResultSource`** (B2) — 에이전트 precompute 결과 조회. 계약이 동일하므로
  `main.py`의 `content_source = ...` 주입만 바꾸면 교체 완료.

## 게이팅 경계 (청크 끝 = 공개 지점)
`c1<215? empty · ≥215 c1 · ≥320 c2 · ≥380 c3`. 청크를 **끝까지** 읽어야 그 청크 fact 공개.
