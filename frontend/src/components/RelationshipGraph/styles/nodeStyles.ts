export function nodeSize(score: number) {
  if (score >= 5) return 86;
  if (score >= 4) return 74;
  if (score >= 3) return 62;
  if (score >= 2) return 54;
  return 48;
}

export function nodeBorderWidth(score: number) {
  if (score >= 5) return 2;
  if (score >= 4) return 1.75;
  if (score >= 3) return 1.5;
  return 1.25;
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
      // 색을 아예 옅은 파스텔로 바꿨더니 너무 흐려 보인다는 피드백이 있어, 원래
      // 진한 그룹 색(data(color))을 다시 쓰되 불투명도만 낮춰서 눈이 덜 아프게 한다.
      'background-opacity': 0.78,
      'border-color': '#ffffff',
      'border-width': 'data(borderWidth)',
      'bounds-expansion': 16,
      // 이름만 원 중심에 넣는다(설명은 별도의 위성 노드로 그 위에 따로 붙는다 —
      // makeElements의 node-caption, 아래 '.node-caption' 스타일 참고). 흰 배경
      // 박스는 지웠다 — 원 색 위에 글자만 바로 얹는다.
      label: 'data(label)',
      color: '#ffffff',
      'font-size': 12,
      'font-weight': 900,
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'wrap',
      'text-max-width': 'data(size)',
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
      'border-width': 2.25,
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
  // 사망이 확인된 인물(characterStatus.isDeceased) — 채움을 더 흐릿하게 하고 테두리를
  // 점선으로 바꿔서 "더 이상 이야기 안에 없는 사람"이라는 게 한눈에 보이게 한다.
  // 이름 앞에 "故"도 붙는다(makeElements 참고).
  {
    selector: 'node.deceased',
    style: {
      'background-opacity': 0.45,
      'border-style': 'dashed',
      'shadow-opacity': 0.06,
    },
  },
  {
    selector: 'node:hover',
    style: {
      width: 'data(hoverSize)',
      height: 'data(hoverSize)',
      'border-color': '#0f172a',
      'border-width': 2.25,
      'z-index': 30,
    },
  },
  {
    selector: '.focused',
    style: {
      opacity: 1,
      'z-index': 40,
      'border-color': '#0f172a',
      'border-width': 2.5,
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
      'border-width': 2.5,
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
      'border-width': 2.25,
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
  // 설명(직업 등) 전용 위성 노드 — 원도 테두리도 그림자도 없이 텍스트만 보이는
  // 투명한 점 하나다. 본체 노드 바로 위에 위치가 계속 동기화된다
  // (FullscreenRelationshipGraph의 syncCaptionPosition 참고). 흰 배경 박스 없이
  // 캔버스 배경(연한 회색) 위에 바로 글자만 얹는다.
  {
    selector: '.node-caption',
    style: {
      width: 1,
      height: 1,
      'background-opacity': 0,
      'border-width': 0,
      'shadow-opacity': 0,
      events: 'no',
      label: 'data(label)',
      color: '#475569',
      'font-size': 10,
      'font-weight': 600,
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'wrap',
      'text-max-width': 100,
      'z-index': 3,
    },
  },
];
