// ── 공유 상수 (SPEC §1 청크 경계) ─────────────────────────────
export const BOOK_ID = 'b_mist';

// 청크 경계 (strict_chunk_end) — 이 값을 넘어 끝까지 읽어야 fact 공개
export const CHUNK_BOUNDARIES = [215, 320, 380, 430] as const;

// 노드 타입 라벨
export const TYPE_LABEL: Record<string, string> = {
  person: '인물',
  ship: '함선',
  org: '조직',
  place: '장소',
};

export const TONE_LABEL: Record<string, string> = {
  ally: '우호',
  tense: '긴장',
  neutral: '중립',
};
