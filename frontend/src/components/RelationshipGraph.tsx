import { useState } from 'react';
import type { GraphJson } from '../api/types';
import { FullscreenRelationshipGraph } from './FullscreenRelationshipGraph';

export function RelationshipGraph({ graph }: { graph: GraphJson }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm font-bold text-slate-600 shadow-sm transition hover:border-accent hover:bg-indigo-50 hover:text-accent"
        aria-label="관계도 보기"
      >
        관계도 보기
      </button>
      <FullscreenRelationshipGraph
        open={expanded}
        onClose={() => setExpanded(false)}
        entities={graph.entities}
        relationships={graph.relationships}
      />
    </>
  );
}
