export function nodeSize(score: number) {
  if (score >= 5) return 86;
  if (score >= 4) return 74;
  if (score >= 3) return 62;
  if (score >= 2) return 54;
  return 48;
}

export function nodeBorderWidth(score: number) {
  if (score >= 5) return 6;
  if (score >= 4) return 5;
  if (score >= 3) return 4;
  return 3;
}

export function shortNodeName(name: string) {
  const cleaned = name.trim();
  if (!cleaned) return '';
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (/[가-힣]/.test(cleaned)) return cleaned.slice(0, 2);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return parts
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export const nodeStyles = [
  {
    selector: 'node',
    style: {
      display: 'element',
      visibility: 'visible',
      opacity: 1,
      width: 'data(size)',
      height: 'data(size)',
      shape: 'ellipse',
      'background-color': 'data(color)',
      'border-color': '#ffffff',
      'border-width': 'data(borderWidth)',
      'bounds-expansion': 16,
      label: 'data(label)',
      color: '#ffffff',
      'font-size': 11,
      'font-weight': 900,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.9,
      'text-background-padding': 2,
      'text-background-shape': 'roundrectangle',
      'background-image': 'data(icon)',
      'background-fit': 'contain',
      'background-clip': 'none',
      'overlay-opacity': 0,
      'shadow-blur': 14,
      'shadow-color': '#0f172a',
      'shadow-opacity': 0.18,
      'shadow-offset-x': 0,
      'shadow-offset-y': 6,
      'z-index': 10,
    },
  },
  {
    selector: 'node[score >= 5]',
    style: {
      'border-color': '#f8fafc',
      'border-width': 7,
      'shadow-blur': 26,
      'shadow-color': 'data(borderColor)',
      'shadow-opacity': 0.45,
      'z-index': 18,
    },
  },
  {
    selector: 'node[score <= 2]',
    style: {
      opacity: 0.72,
      'font-size': 10,
      'shadow-opacity': 0.08,
    },
  },
  {
    selector: 'node:hover',
    style: {
      width: 'data(hoverSize)',
      height: 'data(hoverSize)',
      'border-color': '#0f172a',
      'border-width': 6,
      'z-index': 30,
    },
  },
  {
    selector: '.focused',
    style: {
      opacity: 1,
      'z-index': 40,
      'border-color': '#0f172a',
      'border-width': 7,
      width: 'data(focusSize)',
      height: 'data(focusSize)',
    },
  },
  {
    selector: '.neighbor',
    style: {
      opacity: 1,
      'z-index': 25,
    },
  },
  {
    selector: '.matched',
    style: {
      'border-color': '#f59e0b',
      'border-width': 7,
      'shadow-color': '#f59e0b',
      'shadow-opacity': 0.4,
    },
  },
  {
    selector: '.group-highlight',
    style: {
      opacity: 1,
      'z-index': 22,
      'border-color': 'data(borderColor)',
      'border-width': 6,
    },
  },
  {
    selector: '.group-muted',
    style: {
      opacity: 0.16,
    },
  },
  {
    selector: '.faded',
    style: {
      opacity: 0.14,
    },
  },
];
