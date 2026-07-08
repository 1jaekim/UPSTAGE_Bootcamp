import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
DEFAULT_BOOK_ID = os.getenv("SPO_BOOK_ID", "")
EPUB_PATH = os.getenv("SPO_EPUB_PATH", "")

# cfi_db의 chapter_index(0=서문, 1~15=본문 챕터)와 agents.parsers.epub_parser의
# chapter_index(표지·목차 등 앞부분 문서까지 포함해 1부터 순서대로 매김) 사이의 오프셋.
# 셜록 홈즈 EPUB 기준으로 실측한 고정값 — 다른 책을 붙일 땐 재검증 필요.
PARSER_CHAPTER_OFFSET = 2
