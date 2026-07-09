import type { GraphJson, Relationship } from '../api/types';
import { useSpoStore } from '../store';

const CATEGORY_STYLE: Record<string, string> = {
  ally: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  family: 'bg-violet-50 text-violet-700 border-violet-200',
  conflict: 'bg-rose-50 text-rose-700 border-rose-200',
  romance: 'bg-pink-50 text-pink-700 border-pink-200',
  work: 'bg-sky-50 text-sky-700 border-sky-200',
  mystery: 'bg-amber-50 text-amber-700 border-amber-200',
  neutral: 'bg-slate-50 text-slate-600 border-slate-200',
};

const CATEGORY_LABEL: Record<string, string> = {
  ally: '협력',
  family: '가족',
  conflict: '갈등',
  romance: '감정',
  work: '업무',
  mystery: '단서',
  neutral: '관련',
};

function maskName(name: string, mask: boolean) {
  if (!mask) return name;
  return name[0] + '•'.repeat(Math.max(name.length - 1, 1));
}

function nameOf(graph: GraphJson, id: string): string {
  return graph.entities.find((entity) => entity.id === id)?.name ?? id;
}

function relationLabel(relationship: Relationship) {
  return relationship.display_label || relationship.label || '관련';
}

export function RelationshipList({ graph }: { graph: GraphJson }) {
  const maskNames = useSpoStore((s) => s.maskNames);

  return (
    <ul className="space-y-2">
      {graph.relationships.map((relationship) => {
        const src = maskName(nameOf(graph, relationship.source), maskNames);
        const tgt = maskName(nameOf(graph, relationship.target), maskNames);
        const category = relationship.relation_category ?? 'neutral';
        return (
          <li
            key={relationship.id}
            className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-800">
              <span>{src}</span>
              <span className="text-slate-300">
                {relationship.directionality === 'directed' ? '→' : '—'}
              </span>
              <span>{tgt}</span>
              <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                {relationLabel(relationship)}
              </span>
              {relationship.is_new_at_current_position && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                  새 관계
                </span>
              )}
              <span
                className={`ml-auto rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                  CATEGORY_STYLE[category] ?? CATEGORY_STYLE.neutral
                }`}
              >
                {CATEGORY_LABEL[category] ?? category}
              </span>
            </div>
            <p className="mt-1.5 whitespace-pre-line text-xs leading-5 text-slate-500">
              {relationship.detail || relationship.description}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
