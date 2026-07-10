import type { Core, LayoutOptions } from 'cytoscape';

export const FIT_PADDING = 80;

export function gridLayoutOptions(): LayoutOptions {
  return {
    name: 'grid',
    fit: true,
    padding: FIT_PADDING,
    animate: false,
  } as LayoutOptions;
}

export function coseLayoutOptions(): LayoutOptions {
  return {
    name: 'cose',
    fit: true,
    padding: FIT_PADDING,
    animate: true,
    animationDuration: 650,
    randomize: false,
    componentSpacing: 140,
    nodeOverlap: 24,
    nodeRepulsion: 700000,
    idealEdgeLength: 180,
    edgeElasticity: 90,
    nestingFactor: 1.2,
    gravity: 0.18,
    numIter: 1200,
  } as LayoutOptions;
}

export function seedGroupedPositions(cy: Core) {
  const nodes = cy.nodes();
  if (nodes.length === 0) return;

  const groups = Array.from(new Set(nodes.map((node) => String(node.data('groupId') || 'other'))));
  const centerX = Math.max(cy.width() / 2, 400);
  const centerY = Math.max(cy.height() / 2, 300);
  const radius = Math.max(180, Math.min(cy.width(), cy.height()) * 0.28);
  const grouped = new Map<string, typeof nodes>();

  groups.forEach((groupId) => {
    grouped.set(groupId, nodes.filter((node) => node.data('groupId') === groupId));
  });

  groups.forEach((groupId, groupIndex) => {
    const angle = (Math.PI * 2 * groupIndex) / Math.max(groups.length, 1);
    const groupNodes = grouped.get(groupId);
    if (!groupNodes) return;
    const groupCenter = {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };

    groupNodes.forEach((node, nodeIndex) => {
      const score = Number(node.data('score') || 1);
      const nodeRadius = score >= 5 ? radius * 0.12 : score >= 4 ? radius * 0.34 : radius * 0.62;
      const nodeAngle = angle + (Math.PI * 2 * nodeIndex) / Math.max(groupNodes.length, 1);
      node.position({
        x: score >= 5 ? centerX : groupCenter.x + Math.cos(nodeAngle) * nodeRadius,
        y: score >= 5 ? centerY : groupCenter.y + Math.sin(nodeAngle) * nodeRadius,
      });
    });
  });
}

export function runFullscreenLayout(cy: Core, onStop?: () => void) {
  cy.resize();
  seedGroupedPositions(cy);

  try {
    const layout = cy.layout(coseLayoutOptions());
    layout.one('layoutstop', () => {
      onStop?.();
    });
    layout.run();
  } catch (error) {
    console.error('Relationship graph cose layout failed; using grid fallback.', error);
    const fallback = cy.layout(gridLayoutOptions());
    fallback.one('layoutstop', () => {
      onStop?.();
    });
    fallback.run();
  }
}
