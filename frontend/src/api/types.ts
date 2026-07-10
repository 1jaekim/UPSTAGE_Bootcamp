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
  importance_score?: number;
  importance_level?: 'major' | 'minor';
}

export interface Relationship {
  id: string;
  source: string; // entity id
  target: string; // entity id
  label: string;
  tone: RelationTone;
  description: string;
  revision_offset: number;
  display_label?: string | null;
  relation_category?:
    | 'ally'
    | 'family'
    | 'conflict'
    | 'crime'
    | 'investigation'
    | 'deception'
    | 'protection'
    | 'romance'
    | 'work'
    | 'mystery'
    | 'neutral';
  directionality?: 'directed' | 'undirected';
  relation_importance_score?: number;
  relation_importance_level?: 'major' | 'minor';
  first_seen_global_index?: number | null;
  first_seen_boundary?: number | null;
  is_new_at_current_position?: boolean;
  detail?: string | null;
  event_name?: string | null;
  event_summary?: string | null;
  relation_role?: string | null;
  role_label?: string | null;
  role_pair_label?: string | null;
  relationship_summary?: string | null;
  evidence?: string[];
  confidence?: number;
  is_story_relation?: boolean;
  last_seen_global_index?: number | null;
  related_events?: Array<Record<string, unknown>>;
}

/** 계약 graph_json */
export interface GraphJson {
  offset: number;
  spoiler_safe: boolean;
  entities: Entity[];
  relationships: Relationship[];
  events?: Array<Record<string, unknown>>;
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
