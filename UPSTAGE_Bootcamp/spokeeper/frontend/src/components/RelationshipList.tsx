// ── 관계 카드 리스트 (F2): 병합 엣지 1줄씩 ─────────────────────
import { useMemo } from 'react';
import type { GraphJson } from '../api/types';
import { TONE_LABEL } from '../lib/constants';
import { mergeEdges, nameOf } from '../lib/mergeEdges';
import { useSpoStore } from '../store';

const TONE_STYLE: Record<string, string> = {
  ally: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  tense: 'bg-rose-50 text-rose-700 border-rose-200',
  neutral: 'bg-slate-50 text-slate-600 border-slate-200',
};

function maskName(name: string, mask: boolean) {
  if (!mask) return name;
  return name[0] + '•'.repeat(Math.max(name.length - 1, 1));
}

export function RelationshipList({ graph }: { graph: GraphJson }) {
  const maskNames = useSpoStore((s) => s.maskNames);
  const merged = useMemo(() => mergeEdges(graph.relationships), [graph.relationships]);

  return (
    <ul className="space-y-2">
      {merged.map((edge) => {
        const src = maskName(nameOf(graph.entities, edge.source), maskNames);
        const targets = edge.targets
          .map((t) => maskName(nameOf(graph.entities, t), maskNames))
          .join('/'); // 병합 표시: 민우/서현
        return (
          <li
            key={edge.key}
            className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <span>{src}</span>
              <span className="text-slate-300">—</span>
              <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                {edge.label}
              </span>
              <span className="text-slate-300">—</span>
              <span>{targets}</span>
              <span
                className={`ml-auto rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                  TONE_STYLE[edge.tone] ?? TONE_STYLE.neutral
                }`}
              >
                {TONE_LABEL[edge.tone] ?? edge.tone}
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-5 text-slate-500">{edge.description}</p>
          </li>
        );
      })}
    </ul>
  );
}
