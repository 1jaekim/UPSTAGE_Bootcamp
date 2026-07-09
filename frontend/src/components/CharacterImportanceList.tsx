import { useState } from 'react';
import type { Entity } from '../api/types';
import { TYPE_LABEL } from '../lib/constants';

function stars(score?: number) {
  const value = Math.max(1, Math.min(5, score ?? 1));
  return '★'.repeat(value) + '☆'.repeat(5 - value);
}

function CharacterPill({ entity }: { entity: Entity }) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      <span className="min-w-0">
        <span className="font-medium text-slate-700">{entity.name}</span>
        <span className="ml-1 text-[10px] text-slate-400">
          {TYPE_LABEL[entity.type] ?? entity.type}
        </span>
      </span>
      <span className="shrink-0 text-[11px] tracking-wide text-amber-500">
        {stars(entity.importance_score)}
      </span>
    </li>
  );
}

export function CharacterImportanceList({ entities }: { entities: Entity[] }) {
  const [showMinor, setShowMinor] = useState(false);
  const sorted = [...entities].sort(
    (a, b) => (b.importance_score ?? 1) - (a.importance_score ?? 1) || a.name.localeCompare(b.name),
  );
  const major = sorted.filter((entity) => entity.importance_level === 'major');
  const minor = sorted.filter((entity) => entity.importance_level !== 'major');

  return (
    <div className="space-y-3">
      <div>
        <div className="mb-2 text-xs font-semibold text-slate-500">
          주요 등장인물 ({major.length})
        </div>
        <ul className="space-y-1.5">
          {(major.length ? major : sorted.slice(0, 3)).map((entity) => (
            <CharacterPill key={entity.id} entity={entity} />
          ))}
        </ul>
      </div>

      {minor.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowMinor((value) => !value)}
            className="mb-2 text-xs font-semibold text-slate-500 transition hover:text-slate-700"
          >
            기타 등장인물 ({minor.length}) {showMinor ? '접기' : '펼치기'}
          </button>
          {showMinor && (
            <ul className="space-y-1.5">
              {minor.map((entity) => (
                <CharacterPill key={entity.id} entity={entity} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
