import type cytoscape from 'cytoscape';

export const CATEGORY_COLOR: Record<string, string> = {
  ally: '#16a34a',
  family: '#2563eb',
  investigation: '#0284c7',
  conflict: '#dc2626',
  crime: '#991b1b',
  romance: '#db2777',
  deception: '#7c3aed',
  protection: '#0f766e',
  work: '#f97316',
  mystery: '#d97706',
  neutral: '#64748b',
};

export const edgeStyles = [
  {
    selector: 'edge',
    style: {
      width: 'data(width)',
      opacity: 'data(opacity)',
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': (edge: cytoscape.SingularElementArgument) =>
        edge.data('directed') ? 'triangle' : 'none',
      'arrow-scale': 1.1,
      'curve-style': 'bezier',
      'control-point-step-size': 42,
      label: 'data(visibleLabel)',
      color: '#334155',
      'font-size': 10,
      'font-weight': 800,
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.92,
      'text-background-padding': 2,
      'text-background-shape': 'roundrectangle',
      'overlay-opacity': 0,
      'z-index': 4,
    },
  },
  {
    selector: 'edge[majorLabel = "true"]',
    style: {
      'text-opacity': 1,
      width: 3,
      opacity: 0.82,
    },
  },
  {
    selector: 'edge:hover',
    style: {
      width: 5,
      opacity: 1,
      label: 'data(label)',
      'z-index': 35,
    },
  },
  {
    selector: 'edge.focused',
    style: {
      width: 5,
      opacity: 1,
      label: 'data(label)',
      'z-index': 38,
    },
  },
  {
    selector: 'edge.faded',
    style: {
      opacity: 0.1,
    },
  },
  {
    selector: 'edge.group-highlight',
    style: {
      width: 4,
      opacity: 0.92,
    },
  },
  {
    selector: 'edge.group-muted',
    style: {
      opacity: 0.08,
    },
  },
];
