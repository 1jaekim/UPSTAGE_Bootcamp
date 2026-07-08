// ── 통합 계약 타입 (SPEC §0.5) ────────────────────────────────
// FE / BE / 에이전트가 오직 이 스키마로만 주고받는다. 절대 변경 금지.

export type EntityType = 'person' | 'ship' | 'org' | 'place';
export type NodeColor = 'blue' | 'dark';
export type RelationTone = 'neutral' | 'ally' | 'tense';

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  color: NodeColor;
}

export interface Relationship {
  id: string;
  source: string; // entity id
  target: string; // entity id
  label: string;
  tone: RelationTone;
  description: string;
  revision_offset: number;
}

/** 계약 graph_json */
export interface GraphJson {
  offset: number;
  spoiler_safe: boolean;
  entities: Entity[];
  relationships: Relationship[];
}

export interface ReminderLine {
  text: string;
  entity_ids: string[];
}

/** 계약 reminders */
export interface Reminders {
  offset: number;
  lines: ReminderLine[];
}

// ── 서빙 메타 (계약 외 부수 리소스) ────────────────────────────
export interface Part {
  id: string;
  index: number;
  title: string;
  start_offset: number;
  end_offset: number;
}

export interface Chapter {
  id: string;
  part_id?: string;
  index: number;
  title: string;
  start_offset: number;
  end_offset: number;
  content?: string;
}

export interface Book {
  id: string;
  title: string;
  author: string;
  total_offset: number;
  parts: Part[];
  chapters: Chapter[];
}

export interface Progress {
  user_id: string;
  book_id: string;
  reading_offset: number;
  spoiler_boundary: number;
  cfi?: string | null;
}

export interface BookSummary {
  id: string;
  title: string;
  author: string;
  total_offset: number;
}

export interface UploadResult {
  book_id: string;
  reused: boolean;
  paragraph_count: number;
}
