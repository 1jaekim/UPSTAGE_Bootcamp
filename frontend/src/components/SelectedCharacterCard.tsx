import type { Entity } from '../api/types';
import { TYPE_LABEL } from '../lib/constants';

function score(entity: Entity) {
  return Math.max(1, Math.min(5, entity.importance_score ?? (entity.importance_level === 'major' ? 4 : 2)));
}

function stars(value: number) {
  return `${'★'.repeat(value)}${'☆'.repeat(5 - value)}`;
}

export function SelectedCharacterCard({ entity }: { entity: Entity }) {
  const value = score(entity);
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-black tracking-wide text-amber-500">{stars(value)}</div>
      <h3 className="text-xl font-extrabold text-slate-900">{entity.name}</h3>
      <p className="mt-1 text-sm font-semibold text-slate-500">
        {TYPE_LABEL[entity.type] ?? entity.type}
        {entity.importance_level === 'major' ? ' · 핵심 인물' : ' · 등장인물'}
      </p>
      {entity.description && (
        <p className="mt-1 text-xs font-medium leading-snug text-slate-400">{entity.description}</p>
      )}
    </section>
  );
}
