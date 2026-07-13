import { useSpoStore } from '../store';
import { RelationPanel } from './RelationPanel';
import { ReminderPanel } from './ReminderPanel';
import { SettingsPanel } from './SettingsPanel';

export function SidePanel() {
  const panel = useSpoStore((s) => s.panel);
  const setPanel = useSpoStore((s) => s.setPanel);
  const currentPage = useSpoStore((s) => s.currentPage);

  // 예전엔 'hidden lg:flex'였는데, lg 브레이크포인트에서 lg:flex가 hidden을 덮어써서
  // 데스크탑 화면에선 panel이 'closed'여도 사이드바가 절대 안 사라지는 버그가 있었다.
  // 아예 렌더링 자체를 안 하는 쪽이 화면 크기와 무관하게 확실하다 — 그리고
  // ReaderLayout이 grid-cols를 panel 상태에 맞춰 접어야 빈 칸도 안 남는다.
  if (panel === 'closed') return null;

  return (
    <aside className="flex min-h-0 flex-col border-l border-slate-200 bg-white shadow-[-8px_0_20px_rgba(15,23,42,0.035)]">
      <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-slate-100 bg-slate-50 px-5">
        <div>
          <h2 className="text-[15px] font-bold text-slate-800">
            {panel === 'relationship' && '관계도'}
            {panel === 'reminder' && '요약'}
            {panel === 'settings' && '설정'}
          </h2>
          <p className="text-xs font-semibold text-slate-400">
            {currentPage > 0 ? `현재 ${currentPage}페이지까지 공개된 정보` : '페이지 계산 중'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setPanel('closed')}
          className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-lg leading-none text-slate-500 transition hover:border-slate-300 hover:text-slate-800"
          aria-label="패널 닫기"
        >
          ×
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {panel === 'relationship' && <RelationPanel />}
        {panel === 'reminder' && <ReminderPanel />}
        {panel === 'settings' && <SettingsPanel />}
      </div>
    </aside>
  );
}
