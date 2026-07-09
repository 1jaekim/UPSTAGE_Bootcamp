import { useMemo, useState } from 'react';
import type { GraphJson, Relationship } from '../api/types';
import { useSpoStore } from '../store';

const NODE_W = 132;
const NODE_H = 46;
const VIEW_W = 620;
const VIEW_H = 430;
const CX = VIEW_W / 2;
const CY = VIEW_H / 2;

const CATEGORY_STROKE: Record<string, string> = {
  ally: '#22c55e',
  family: '#8b5cf6',
  conflict: '#ef4444',
  romance: '#ec4899',
  work: '#0ea5e9',
  mystery: '#f59e0b',
  neutral: '#94a3b8',
};

function maskName(name: string, mask: boolean) {
  if (!mask) return name;
  return name[0] + '•'.repeat(Math.max(name.length - 1, 1));
}

function relationLabel(relationship: Relationship) {
  return relationship.display_label || relationship.label || '관련';
}

export function RelationshipGraph({ graph }: { graph: GraphJson }) {
  const maskNames = useSpoStore((s) => s.maskNames);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedRelation, setSelectedRelation] = useState<Relationship | null>(null);

  const connectedIds = useMemo(() => {
    if (!selectedNodeId) return null;
    const ids = new Set([selectedNodeId]);
    graph.relationships.forEach((relationship) => {
      if (relationship.source === selectedNodeId || relationship.target === selectedNodeId) {
        ids.add(relationship.source);
        ids.add(relationship.target);
      }
    });
    return ids;
  }, [graph.relationships, selectedNodeId]);

  const pos = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    const count = Math.max(graph.entities.length, 1);
    const radiusX = Math.min(230, 120 + count * 8);
    const radiusY = Math.min(145, 85 + count * 5);
    graph.entities.forEach((entity, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
      m.set(entity.id, {
        x: CX + Math.cos(angle) * radiusX,
        y: CY + Math.sin(angle) * radiusY,
      });
    });
    return m;
  }, [graph.entities]);

  return (
    <div className="space-y-3">
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="w-full"
        role="img"
        aria-label="인물 관계도"
      >
        <defs>
          {Object.entries(CATEGORY_STROKE).map(([category, color]) => (
            <marker
              key={category}
              id={`arrow-${category}`}
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
            </marker>
          ))}
        </defs>

        {graph.relationships.map((relationship) => {
          const source = pos.get(relationship.source);
          const target = pos.get(relationship.target);
          if (!source || !target) return null;
          const category = relationship.relation_category ?? 'neutral';
          const stroke = CATEGORY_STROKE[category] ?? CATEGORY_STROKE.neutral;
          const isConnected =
            !connectedIds || connectedIds.has(relationship.source) || connectedIds.has(relationship.target);
          const mx = (source.x + target.x) / 2;
          const my = (source.y + target.y) / 2;
          const isNew = relationship.is_new_at_current_position;

          return (
            <g
              key={relationship.id}
              opacity={isConnected ? 1 : 0.18}
              onClick={() => setSelectedRelation(relationship)}
              className="cursor-pointer"
            >
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={stroke}
                strokeWidth={isNew ? 3 : 2}
                strokeDasharray={relationship.relation_importance_level === 'minor' ? '5 5' : undefined}
                markerEnd={relationship.directionality === 'directed' ? `url(#arrow-${category})` : undefined}
              />
              <rect
                x={mx - relationLabel(relationship).length * 6 - 18}
                y={my - 12}
                width={relationLabel(relationship).length * 12 + (isNew ? 56 : 24)}
                height={24}
                rx={12}
                fill="#fff"
                stroke={stroke}
                strokeWidth={1}
              />
              <text x={mx} y={my + 4} textAnchor="middle" fontSize={11} fill="#334155" fontWeight={700}>
                {relationLabel(relationship)}
                {isNew ? ' · 새 관계' : ''}
              </text>
              <title>{relationship.detail || relationship.description}</title>
            </g>
          );
        })}

        {graph.entities.map((entity) => {
          const p = pos.get(entity.id)!;
          const isFocused = !connectedIds || connectedIds.has(entity.id);
          const fill = entity.importance_level === 'major' ? '#2437c7' : '#475569';
          return (
            <g
              key={entity.id}
              opacity={isFocused ? 1 : 0.22}
              onClick={() => {
                setSelectedNodeId((current) => (current === entity.id ? null : entity.id));
                setSelectedRelation(null);
              }}
              className="cursor-pointer"
            >
              <rect
                x={p.x - NODE_W / 2}
                y={p.y - NODE_H / 2}
                width={NODE_W}
                height={NODE_H}
                rx={10}
                fill={fill}
              />
              <text x={p.x} y={p.y - 2} textAnchor="middle" fontSize={13} fontWeight={700} fill="#fff">
                {maskName(entity.name, maskNames)}
              </text>
              <text x={p.x} y={p.y + 14} textAnchor="middle" fontSize={10} fill="#dbeafe">
                {'★'.repeat(entity.importance_score ?? 1)}
              </text>
            </g>
          );
        })}
      </svg>

      {selectedRelation && (
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-600 shadow-sm">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-semibold text-slate-800">{relationLabel(selectedRelation)}</span>
            {selectedRelation.is_new_at_current_position && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                새 관계
              </span>
            )}
          </div>
          <p>{selectedRelation.detail || selectedRelation.description}</p>
        </div>
      )}
    </div>
  );
}
