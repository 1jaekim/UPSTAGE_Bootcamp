// ── 레이아웃 구성은 main app.py를 따른다: 사이드바 | EPUB 뷰어 | SpoKeeper 패널 ──
// 시각 스타일은 기존 React 디자인 토큰(accent·slate·rounded·shadow)을 유지한다.
import { Sidebar } from './components/Sidebar';
import { EpubViewer } from './components/EpubViewer';
import { SpoKeeperPanel } from './components/SpoKeeperPanel';

export default function App() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <EpubViewer />
        <SpoKeeperPanel />
      </main>
    </div>
  );
}
