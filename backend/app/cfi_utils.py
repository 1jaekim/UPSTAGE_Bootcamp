"""EPUB CFI 문자열 <-> 정렬용 정수 배열 변환.

Supabase book_cfi_index.cfi_path(INTEGER[])와 동일한 규칙으로 변환해야 global_index
매칭이 정확하다. spokeeper_cfi_db/cfi_utils.py와 동일 로직 (mismatch 0건 검증됨).
"""
import re


def cfi_to_path(cfi: str) -> list[int]:
    """EPUB CFI 문자열을 정렬 비교용 정수 배열로 변환.

    예: "epubcfi(/6/10!/2/4/2[pgepubid00003]/4/1)" -> [6,0,10,0,2,0,4,0,2,0,4,0,1,0]
    """
    inner = re.sub(r'^epubcfi\((.*)\)$', r'\1', cfi.strip())
    inner = re.sub(r'\[[^\]]*\]', '', inner)  # ID 어설션 제거
    inner = inner.replace('!', '/')            # indirection -> 경로 연속

    steps: list[int] = []
    for token in inner.split('/'):
        if not token:
            continue
        if ':' in token:
            step, offset = token.split(':')
            steps.append(int(step))
            steps.append(int(offset))
        else:
            steps.append(int(token))
            steps.append(0)
    return steps
