import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react';
import cytoscape, { type Core, type ElementDefinition, type EventObject } from 'cytoscape';
import type { Entity, GraphJson, Relationship } from '../api/types';
import { useSpoStore } from '../store';

const NODE_W = 132;
const NODE_H = 46;
const COMPACT_VIEW_W = 620;
const COMPACT_VIEW_H = 430;
const MIN_ZOOM = 0.45;
const MAX_ZOOM = 2.4;

const CATEGORY_STROKE: Record<string, string> = {
  ally: '#22c55e',
  family: '#8b5cf6',
  conflict: '#ef4444',
  romance: '#ec4899',
  work: '#0ea5e9',
  mystery: '#f59e0b',
  neutral: '#94a3b8',
};

const COMPACT_LAYOUT = {
  nodeRepulsion: 8,
  idealEdgeLength: 120,
  spacingFactor: 1,
  padding: 36,
};

const SPACIOUS_LAYOUT = {
  nodeRepulsion: 12000,
  idealEdgeLength: 230,
  spacingFactor: 1.9,
  padding: 120,
};

function maskName(name: string, mask: boolean) {
  if (!mask) return name;
  return name[0] + '•'.repeat(Math.max(name.length - 1, 1));
}

function relationLabel(relationship: Relationship) {
  return relationship.display_label || relationship.label || '관계';
}

function relationDetail(relationship: Relationship) {
  return relationship.detail || relationship.description || relationLabel(relationship);
}

function compactPositions(graph: GraphJson) {
  const positions = new Map<string, { x: number; y: number }>();
  const count = Math.max(graph.entities.length, 1);
  const cx = COMPACT_VIEW_W / 2;
  const cy = COMPACT_VIEW_H / 2;
  const radiusX = Math.min(
    COMPACT_VIEW_W / 2 - COMPACT_LAYOUT.padding,
    COMPACT_LAYOUT.idealEdgeLength * COMPACT_LAYOUT.spacingFactor + count * COMPACT_LAYOUT.nodeRepulsion,
  );
  const radiusY = Math.min(
    COMPACT_VIEW_H / 2 - COMPACT_LAYOUT.padding,
    COMPACT_LAYOUT.idealEdgeLength * 0.7 + count * COMPACT_LAYOUT.nodeRepulsion,
  );

  graph.entities.forEach((entity, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    positions.set(entity.id, {
      x: cx + Math.cos(angle) * radiusX,
      y: cy + Math.sin(angle) * radiusY,
    });
  });

  return positions;
}

function CompactGraphCanvas({ graph, search }: { graph: GraphJson; search: string }) {
  const maskNames = useSpoStore((state) => state.maskNames);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedRelation, setSelectedRelation] = useState<Relationship | null>(null);
  const query = search.trim().toLowerCase();

  const matchingIds = useMemo(() => {
    if (!query) return null;
    return new Set(
      graph.entities
        .filter((entity) => entity.name.toLowerCase().includes(query))
        .map((entity) => entity.id),
    );
  }, [graph.entities, query]);

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

  const positions = useMemo(() => compactPositions(graph), [graph]);

  function isNodeVisible(id: string) {
    if (matchingIds && !matchingIds.has(id)) return false;
    if (connectedIds && !connectedIds.has(id)) return false;
    return true;
  }

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${COMPACT_VIEW_W} ${COMPACT_VIEW_H}`} className="w-full" role="img" aria-label="인물 관계도">
        <defs>
          {Object.entries(CATEGORY_STROKE).map(([category, color]) => (
            <marker key={category} id={`arrow-${category}-compact`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
            </marker>
          ))}
        </defs>

        {graph.relationships.map((relationship) => {
          const source = positions.get(relationship.source);
          const target = positions.get(relationship.target);
          if (!source || !target) return null;
          const category = relationship.relation_category ?? 'neutral';
          const stroke = CATEGORY_STROKE[category] ?? CATEGORY_STROKE.neutral;
          const relationVisible = isNodeVisible(relationship.source) && isNodeVisible(relationship.target);
          const mx = (source.x + target.x) / 2;
          const my = (source.y + target.y) / 2;
          const label = relationLabel(relationship);

          return (
            <g key={relationship.id} opacity={relationVisible ? 1 : 0.14} onClick={() => setSelectedRelation(relationship)} className="cursor-pointer">
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={stroke}
                strokeWidth={relationship.is_new_at_current_position ? 3.2 : 2.1}
                strokeDasharray={relationship.relation_importance_level === 'minor' ? '5 5' : undefined}
                markerEnd={relationship.directionality === 'directed' ? `url(#arrow-${category}-compact)` : undefined}
              />
              <rect x={mx - label.length * 6 - 18} y={my - 12} width={label.length * 12 + (relationship.is_new_at_current_position ? 56 : 24)} height={24} rx={12} fill="#fff" stroke={stroke} strokeWidth={1} />
              <text x={mx} y={my + 4} textAnchor="middle" fontSize={11} fill="#334155" fontWeight={700}>
                {label}
                {relationship.is_new_at_current_position ? ' · 새 관계' : ''}
              </text>
            </g>
          );
        })}

        {graph.entities.map((entity) => {
          const position = positions.get(entity.id);
          if (!position) return null;
          const isFocused = isNodeVisible(entity.id);
          const fill = entity.importance_level === 'major' ? '#2437c7' : '#475569';

          return (
            <g
              key={entity.id}
              opacity={isFocused ? 1 : 0.18}
              onClick={() => {
                setSelectedNodeId((current) => (current === entity.id ? null : entity.id));
                setSelectedRelation(null);
              }}
              className="cursor-pointer"
            >
              <rect x={position.x - NODE_W / 2} y={position.y - NODE_H / 2} width={NODE_W} height={NODE_H} rx={10} fill={fill} />
              <text x={position.x} y={position.y - 3} textAnchor="middle" fontSize={13} fontWeight={700} fill="#fff">
                {maskName(entity.name, maskNames)}
              </text>
              <text x={position.x} y={position.y + 15} textAnchor="middle" fontSize={10} fill="#dbeafe">
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
            {selectedRelation.is_new_at_current_position && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">새 관계</span>}
          </div>
          <p className="whitespace-pre-line">{relationDetail(selectedRelation)}</p>
        </div>
      )}
    </div>
  );
}

function makeElements(graph: GraphJson): ElementDefinition[] {
  const nodes: ElementDefinition[] = graph.entities.map((entity: Entity) => ({
    group: 'nodes',
    data: {
      id: entity.id,
      label: entity.name,
      stars: '★'.repeat(entity.importance_score ?? 1),
      major: entity.importance_level === 'major',
    },
  }));

  const edges: ElementDefinition[] = graph.relationships.map((relationship) => ({
    group: 'edges',
    data: {
      id: relationship.id,
      source: relationship.source,
      target: relationship.target,
      label: relationLabel(relationship),
      detail: relationDetail(relationship),
      category: relationship.relation_category ?? 'neutral',
      directed: relationship.directionality === 'directed',
      minor: relationship.relation_importance_level === 'minor',
      isNew: !!relationship.is_new_at_current_position,
    },
  }));

  return [...nodes, ...edges];
}

function runSpaciousLayout(cy: Core) {
  cy.resize();
  cy.layout({
    name: 'cose',
    animate: false,
    nodeRepulsion: SPACIOUS_LAYOUT.nodeRepulsion,
    idealEdgeLength: SPACIOUS_LAYOUT.idealEdgeLength,
    componentSpacing: 170,
    nodeOverlap: 16,
    padding: SPACIOUS_LAYOUT.padding,
    fit: false,
  }).run();
  cy.fit(undefined, SPACIOUS_LAYOUT.padding);
  cy.center();
}

function FullscreenCytoscapeGraph({
  graph,
  search,
  cyRef,
}: {
  graph: GraphJson;
  search: string;
  cyRef: MutableRefObject<Core | null>;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeRelation, setActiveRelation] = useState<{ label: string; detail: string; fixed: boolean } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: makeElements(graph),
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: true,
      wheelSensitivity: 0.18,
      style: [
        {
          selector: 'node',
          style: {
            width: 154,
            height: 54,
            shape: 'round-rectangle',
            'background-color': (element: cytoscape.SingularElementArgument) => (element.data('major') ? '#2437c7' : '#475569'),
            label: 'data(label)',
            color: '#fff',
            'font-size': 13,
            'font-weight': 700,
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': 132,
            'overlay-opacity': 0,
            'border-width': 0,
          },
        },
        {
          selector: 'edge',
          style: {
            width: (element: cytoscape.SingularElementArgument) => (element.data('isNew') ? 4 : 2.4),
            'line-color': (element: cytoscape.SingularElementArgument) => CATEGORY_STROKE[element.data('category')] ?? CATEGORY_STROKE.neutral,
            'target-arrow-color': (element: cytoscape.SingularElementArgument) => CATEGORY_STROKE[element.data('category')] ?? CATEGORY_STROKE.neutral,
            'target-arrow-shape': (element: cytoscape.SingularElementArgument) => (element.data('directed') ? 'triangle' : 'none'),
            'curve-style': 'bezier',
            'control-point-step-size': 46,
            label: 'data(label)',
            color: '#334155',
            'font-size': 11,
            'font-weight': 700,
            'text-background-color': '#fff',
            'text-background-opacity': 1,
            'text-background-padding': 4,
            'text-border-color': '#cbd5e1',
            'text-border-width': 1,
            'text-border-opacity': 0.8,
            'line-style': (element: cytoscape.SingularElementArgument) => (element.data('minor') ? 'dashed' : 'solid'),
            'overlay-opacity': 0,
          },
        },
        { selector: '.faded', style: { opacity: 0.15 } },
        { selector: '.highlighted', style: { opacity: 1, 'z-index': 20 } },
        { selector: '.matched', style: { 'border-width': 3, 'border-color': '#f59e0b' } },
      ] as any,
      layout: {
        name: 'cose',
        animate: false,
        nodeRepulsion: SPACIOUS_LAYOUT.nodeRepulsion,
        idealEdgeLength: SPACIOUS_LAYOUT.idealEdgeLength,
        componentSpacing: 170,
        nodeOverlap: 16,
        padding: SPACIOUS_LAYOUT.padding,
        fit: false,
      },
    });

    cyRef.current = cy;

    requestAnimationFrame(() => {
      requestAnimationFrame(() => runSpaciousLayout(cy));
    });

    cy.on('mouseover', 'node, edge', () => {
      if (containerRef.current) containerRef.current.style.cursor = 'pointer';
    });
    cy.on('mouseout', 'node, edge', () => {
      if (containerRef.current) containerRef.current.style.cursor = 'grab';
    });
    cy.on('mouseover', 'edge', (event: EventObject) => {
      const edge = event.target;
      setActiveRelation({ label: edge.data('label'), detail: edge.data('detail'), fixed: false });
    });
    cy.on('tap', 'edge', (event: EventObject) => {
      const edge = event.target;
      setActiveRelation({ label: edge.data('label'), detail: edge.data('detail'), fixed: true });
    });
    cy.on('tap', 'node', (event: EventObject) => {
      const node = event.target;
      cy.elements().addClass('faded').removeClass('highlighted');
      node.closedNeighborhood().removeClass('faded').addClass('highlighted');
      setActiveRelation(null);
    });
    cy.on('tap', (event: EventObject) => {
      if (event.target === cy) {
        cy.elements().removeClass('faded highlighted');
        setActiveRelation(null);
      }
    });

    return () => {
      cy.destroy();
      if (cyRef.current === cy) cyRef.current = null;
    };
  }, [cyRef, graph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('matched');
    const query = search.trim().toLowerCase();
    if (!query) return;
    cy.nodes().forEach((node) => {
      if (String(node.data('label')).toLowerCase().includes(query)) {
        node.addClass('matched');
      }
    });
  }, [cyRef, search]);

  return (
    <div className="relative h-full min-h-[80vh]">
      <div ref={containerRef} className="h-full min-h-[80vh] w-full cursor-grab rounded-lg bg-white" />
      {activeRelation && (
        <div className="absolute bottom-4 left-4 max-w-xl rounded-lg border border-slate-200 bg-white/95 p-3 text-xs leading-5 text-slate-600 shadow-xl">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-semibold text-slate-800">{activeRelation.label}</span>
            {activeRelation.fixed && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">고정됨</span>}
          </div>
          <p className="whitespace-pre-line">{activeRelation.detail}</p>
        </div>
      )}
    </div>
  );
}

export function RelationshipGraph({ graph }: { graph: GraphJson }) {
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState('');
  const cyRef = useRef<Core | null>(null);

  const fitToScreen = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.resize();
    cy.fit(undefined, 100);
    cy.center();
  };

  const zoomIn = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: Math.min(MAX_ZOOM, cy.zoom() * 1.18), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    cy.center();
  };

  const zoomOut = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: Math.max(MIN_ZOOM, cy.zoom() / 1.18), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    cy.center();
  };

  return (
    <div className="relative">
      <div className="mb-2 flex items-center justify-between gap-2">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="인물 검색"
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 outline-none transition focus:border-accent"
        />
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-800"
          aria-label="관계도 크게 보기"
        >
          크게 보기
        </button>
      </div>

      <CompactGraphCanvas graph={graph} search={search} />

      {expanded && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="flex h-full flex-col rounded-xl bg-slate-50 shadow-2xl">
            <header className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
              <div>
                <h2 className="text-sm font-bold text-slate-800">인물 관계도 크게 보기</h2>
                <p className="text-xs text-slate-400">드래그로 이동하고 휠로 확대하거나 축소할 수 있습니다.</p>
              </div>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="인물 검색"
                className="ml-auto w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 outline-none transition focus:border-accent"
              />
              <button
                type="button"
                onClick={() => setExpanded(false)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-800"
                aria-label="관계도 닫기"
              >
                닫기
              </button>
            </header>
            <div className="flex shrink-0 items-center justify-end gap-2 border-b border-slate-200 bg-white px-4 py-2">
              <button type="button" onClick={zoomOut} className="h-8 w-8 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-600 transition hover:bg-slate-50" aria-label="관계도 축소">-</button>
              <button type="button" onClick={zoomIn} className="h-8 w-8 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-600 transition hover:bg-slate-50" aria-label="관계도 확대">+</button>
              <button type="button" onClick={fitToScreen} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50">
                화면에 맞추기
              </button>
            </div>
            <div className="min-h-0 flex-1 p-4">
              <FullscreenCytoscapeGraph graph={graph} search={search} cyRef={cyRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
