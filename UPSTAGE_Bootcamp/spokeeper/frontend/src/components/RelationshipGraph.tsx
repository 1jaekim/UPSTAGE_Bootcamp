// ── 관계도 그래프 (F2): 2열 노드 + 점선 라벨 엣지 ───────────────
import { useMemo } from 'react';
import type { GraphJson } from '../api/types';
import { mergeEdges } from '../lib/mergeEdges';
import { useSpoStore } from '../store';

const NODE_W = 130;
const NODE_H = 44;
const COL_L = 95;
const COL_R = 265;
const ROW_H = 92;
const TOP = 40;
const VIEW_W = 360;

const TONE_STROKE: Record<string, string> = {
  ally: '#22c55e',
  tense: '#e0555a',
  neutral: '#94a3b8',
};

function maskName(name: string, mask: boolean) {
  if (!mask) return name;
  return name[0] + '•'.repeat(Math.max(name.length - 1, 1));
}

export function RelationshipGraph({ graph }: { graph: GraphJson }) {
  const maskNames = useSpoStore((s) => s.maskNames);
  const merged = useMemo(() => mergeEdges(graph.relationships), [graph.relationships]);

  // 노드 좌표: 인덱스 지그재그로 2열 배치
  const pos = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    graph.entities.forEach((e, i) => {
      const row = Math.floor(i / 2);
      const x = i % 2 === 0 ? COL_L : COL_R;
      m.set(e.id, { x, y: TOP + row * ROW_H });
    });
    return m;
  }, [graph.entities]);

  const rows = Math.ceil(graph.entities.length / 2);
  const viewH = TOP + Math.max(rows, 1) * ROW_H;

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${viewH}`}
      className="w-full"
      role="img"
      aria-label="인물 관계도"
    >
      {/* 엣지 (점선) */}
      {merged.map((edge) => {
        const s = pos.get(edge.source);
        if (!s) return null;
        const stroke = TONE_STROKE[edge.tone] ?? TONE_STROKE.neutral;
        // 타깃 중심 좌표
        const targetPts = edge.targets
          .map((t) => pos.get(t))
          .filter(Boolean) as { x: number; y: number }[];
        const cx = targetPts.reduce((a, p) => a + p.x, 0) / (targetPts.length || 1);
        const cy = targetPts.reduce((a, p) => a + p.y, 0) / (targetPts.length || 1);
        const mx = (s.x + cx) / 2;
        const my = (s.y + cy) / 2;
        return (
          <g key={edge.key}>
            {targetPts.map((p, i) => (
              <line
                key={i}
                x1={s.x}
                y1={s.y}
                x2={p.x}
                y2={p.y}
                stroke={stroke}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                opacity={0.7}
              />
            ))}
            <g>
              <rect
                x={mx - edge.label.length * 6 - 6}
                y={my - 10}
                width={edge.label.length * 12 + 12}
                height={20}
                rx={10}
                fill="#fff"
                stroke={stroke}
                strokeWidth={1}
              />
              <text
                x={mx}
                y={my + 4}
                textAnchor="middle"
                fontSize={11}
                fill="#475569"
                fontWeight={600}
              >
                {edge.label}
              </text>
            </g>
          </g>
        );
      })}

      {/* 노드 */}
      {graph.entities.map((e) => {
        const p = pos.get(e.id)!;
        const fill = e.color === 'dark' ? '#2c3242' : '#2f3edb';
        return (
          <g key={e.id}>
            <rect
              x={p.x - NODE_W / 2}
              y={p.y - NODE_H / 2}
              width={NODE_W}
              height={NODE_H}
              rx={12}
              fill={fill}
            />
            <text
              x={p.x}
              y={p.y + 5}
              textAnchor="middle"
              fontSize={14}
              fontWeight={700}
              fill="#fff"
            >
              {maskName(e.name, maskNames)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
