import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape, { type Core, type ElementDefinition, type EventObject } from 'cytoscape';
import type { Entity, Relationship } from '../api/types';
import {
  deriveCharacterGroups,
  usedGroups,
  type CharacterGroupId,
} from './RelationshipGraph/grouping/deriveCharacterGroup';
import { FIT_PADDING, runFullscreenLayout } from './RelationshipGraph/layout/fullscreen';
import { CATEGORY_COLOR, edgeStyles } from './RelationshipGraph/styles/edgeStyles';
import { nodeBorderWidth, nodeSize, nodeStyles } from './RelationshipGraph/styles/nodeStyles';

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 2.8;

type Detail = {
  title: string;
  detail: string;
  eventName: string;
};

function scoreOf(entity: Entity) {
  return Math.max(1, Math.min(5, entity.importance_score ?? (entity.importance_level === 'major' ? 4 : 2)));
}

function relationLabel(relationship: Relationship) {
  return relationship.display_label || relationship.role_pair_label || relationship.label || '관계';
}

function relationDetail(relationship: Relationship) {
  return relationship.relationship_summary || relationship.event_summary || relationship.description || relationLabel(relationship);
}

function makeElements(entities: Entity[], relationships: Relationship[]) {
  const { groupByEntityId } = deriveCharacterGroups(entities, relationships);
  const nodeIds = new Set<string>();
  const usedEdgeIds = new Set<string>();
  const nodes: ElementDefinition[] = [];

  entities.forEach((entity) => {
    const id = String(entity.id ?? '').trim();
    if (!id || nodeIds.has(id)) return;
    nodeIds.add(id);
    const score = scoreOf(entity);
    const size = nodeSize(score);
    const group = groupByEntityId.get(id);
    const color = group?.color ?? '#64748b';
    const label = entity.name || id;

    nodes.push({
      group: 'nodes',
      data: {
        id,
        label,
        score,
        size,
        hoverSize: size + 8,
        focusSize: size + 16,
        borderWidth: nodeBorderWidth(score),
        color,
        borderColor: group?.borderColor ?? '#475569',
        groupId: group?.id ?? 'other',
        groupLabel: group?.label ?? '기타',
      },
    });
  });

  const edges: ElementDefinition[] = [];
  relationships.forEach((relationship, index) => {
    const source = String(relationship.source ?? '').trim();
    const target = String(relationship.target ?? '').trim();
    if (!source || !target || !nodeIds.has(source) || !nodeIds.has(target)) return;

    const rawId = String(relationship.id || `${source}-${target}-${index}`);
    let id = rawId;
    let suffix = 2;
    while (usedEdgeIds.has(id)) {
      id = `${rawId}-${suffix}`;
      suffix += 1;
    }
    usedEdgeIds.add(id);

    const category = relationship.relation_category ?? 'neutral';
    const relationScore = relationship.relation_importance_score ?? (relationship.relation_importance_level === 'major' ? 4 : 2);
    const majorLabel = relationScore >= 4 || relationship.relation_importance_level === 'major';
    edges.push({
      group: 'edges',
      data: {
        id,
        source,
        target,
        label: relationLabel(relationship),
        visibleLabel: majorLabel ? relationLabel(relationship) : '',
        majorLabel: majorLabel ? 'true' : 'false',
        category,
        color: CATEGORY_COLOR[category] ?? CATEGORY_COLOR.neutral,
        directed: relationship.directionality === 'directed',
        width: majorLabel ? 3 : 2,
        opacity: majorLabel ? 0.82 : 0.38,
        detail: relationDetail(relationship),
        eventName: relationship.event_name ?? '',
      },
    });
  });

  return {
    elements: [...nodes, ...edges],
    nodeCount: nodes.length,
    edgeCount: edges.length,
    groups: usedGroups(groupByEntityId),
  };
}

function clearFocus(cy: Core) {
  cy.elements().removeClass('faded focused neighbor matched');
}

function applyNodeFocus(cy: Core, node: cytoscape.NodeSingular) {
  cy.elements().removeClass('focused neighbor matched').addClass('faded');
  node.removeClass('faded').addClass('focused');
  node.connectedEdges().removeClass('faded').addClass('focused');
  node.neighborhood('node').removeClass('faded').addClass('neighbor');
}

export function FullscreenRelationshipGraph({
  open,
  onClose,
  entities,
  relationships,
}: {
  open: boolean;
  onClose: () => void;
  entities: Entity[];
  relationships: Relationship[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState<Detail | null>(null);
  const [activeGroup, setActiveGroup] = useState<CharacterGroupId | 'all'>('all');
  const { elements, nodeCount, edgeCount, groups } = useMemo(
    () => makeElements(entities, relationships),
    [entities, relationships],
  );

  const fitVisibleNodes = () => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    const visibleNodes = cy.nodes(':visible');
    if (visibleNodes.length > 0) {
      cy.resize();
      cy.fit(visibleNodes, FIT_PADDING);
      cy.center(visibleNodes);
    }
  };

  const runCoseLayout = () => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    runFullscreenLayout(cy, fitVisibleNodes);
  };

  useEffect(() => {
    if (!open || !containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      wheelSensitivity: 0.18,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
      style: [...nodeStyles, ...edgeStyles] as unknown as cytoscape.StylesheetCSS[],
    });

    cyRef.current = cy;

    cy.on('tap', 'node', (event: EventObject) => {
      applyNodeFocus(cy, event.target);
      setDetail(null);
    });
    cy.on('tap', 'edge', (event: EventObject) => {
      const edge = event.target;
      cy.elements().removeClass('focused neighbor matched').addClass('faded');
      edge.removeClass('faded').addClass('focused');
      edge.connectedNodes().removeClass('faded').addClass('neighbor');
      setDetail({
        title: edge.data('label'),
        detail: edge.data('detail'),
        eventName: edge.data('eventName'),
      });
    });
    cy.on('tap', (event: EventObject) => {
      if (event.target === cy) {
        clearFocus(cy);
        setDetail(null);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [open]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!open || !cy || cy.destroyed()) return;
    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });
    clearFocus(cy);
    setDetail(null);
    runCoseLayout();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, elements]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!open || !cy || cy.destroyed()) return;
    cy.nodes().removeClass('matched');
    const query = search.trim().toLowerCase();
    if (!query) return;
    cy.nodes().forEach((node) => {
      if (String(node.data('label')).toLowerCase().includes(query)) node.addClass('matched');
    });
  }, [open, search]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!open || !cy || cy.destroyed()) return;
    cy.elements().removeClass('group-muted group-highlight');
    if (activeGroup === 'all') return;
    cy.nodes().forEach((node) => {
      if (node.data('groupId') === activeGroup) {
        node.addClass('group-highlight');
      } else {
        node.addClass('group-muted');
      }
    });
    cy.edges().forEach((edge) => {
      const inGroup = edge.connectedNodes().some((node) => node.data('groupId') === activeGroup);
      edge.addClass(inGroup ? 'group-highlight' : 'group-muted');
    });
  }, [activeGroup, open, elements]);

  if (!open) return null;

  const zoom = (factor: number) => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    cy.zoom({
      level: Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, cy.zoom() * factor)),
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="flex h-[90vh] w-[min(1180px,96vw)] flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-2xl">
        <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50 px-5">
          <h2 className="text-base font-extrabold text-slate-900">관계도 탐색</h2>
          <button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-xl leading-none text-slate-500 transition hover:border-slate-300 hover:text-slate-800" aria-label="관계도 닫기">
            ×
          </button>
        </header>
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="인물 검색"
            className="h-10 w-72 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-accent focus:ring-2 focus:ring-indigo-100"
          />
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => zoom(1 / 1.18)} className="h-9 w-9 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-600">-</button>
            <button type="button" onClick={() => zoom(1.18)} className="h-9 w-9 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-600">+</button>
            <button type="button" onClick={fitVisibleNodes} className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600">Fit</button>
            <button type="button" onClick={() => cyRef.current?.center()} className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600">Center</button>
            <button type="button" onClick={runCoseLayout} className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600">Reset Layout</button>
          </div>
        </div>
        <div className="relative h-[calc(90vh-120px)] min-h-[600px] w-full">
          <div ref={containerRef} className="absolute inset-0 h-full w-full bg-slate-50" />
          {entities.length === 0 && (
            <div className="absolute inset-0 grid place-items-center bg-slate-50 text-sm font-semibold text-slate-400">
              현재 위치까지 표시할 인물이 없습니다.
            </div>
          )}
          {entities.length > 0 && nodeCount === 0 && (
            <div className="absolute inset-0 grid place-items-center bg-slate-50 text-sm font-semibold text-slate-400">
              표시 가능한 인물 정보가 없습니다.
            </div>
          )}
          <div className="absolute left-4 top-4 max-w-[280px] rounded-lg border border-slate-200 bg-white/92 p-3 text-xs font-bold text-slate-600 shadow-sm">
            <div className="mb-2 text-[11px] uppercase tracking-[0.08em] text-slate-400">Groups</div>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setActiveGroup('all')}
                className={`rounded-full border px-2 py-1 text-[11px] font-extrabold transition ${activeGroup === 'all' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}
              >
                전체
              </button>
              {groups.map((group) => (
                <button
                  key={group.id}
                  type="button"
                  onClick={() => setActiveGroup(group.id)}
                  className={`rounded-full border px-2 py-1 text-[11px] font-extrabold transition ${activeGroup === group.id ? 'text-white' : 'bg-white text-slate-600 hover:border-slate-300'}`}
                  style={{
                    borderColor: activeGroup === group.id ? group.borderColor : '#e2e8f0',
                    backgroundColor: activeGroup === group.id ? group.color : '#ffffff',
                  }}
                >
                  <span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ backgroundColor: group.color }} />
                  {group.label}
                </button>
              ))}
            </div>
            <div className="mt-2 text-[11px] text-slate-400">nodes {nodeCount} · edges {edgeCount}</div>
          </div>
          {detail && (
            <div className="absolute bottom-4 left-4 max-w-xl rounded-lg border border-slate-200 bg-white/95 p-3 text-xs font-semibold leading-5 text-slate-600 shadow-xl">
              <div className="mb-1 text-sm font-extrabold text-slate-800">{detail.title}</div>
              {detail.eventName && <div className="mb-1 text-slate-400">대표 사건: {detail.eventName}</div>}
              <p>{detail.detail}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
