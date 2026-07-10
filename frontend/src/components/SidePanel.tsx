import { useSpoStore } from '../store';
import { RelationPanel } from './RelationPanel';
import { ReminderPanel } from './ReminderPanel';
import { SettingsPanel } from './SettingsPanel';

export function SidePanel() {
  const panel = useSpoStore((s) => s.panel);
  const setPanel = useSpoStore((s) => s.setPanel);

  return (
    <aside className={`${panel === 'closed' ? 'hidden lg:flex' : 'flex'} min-h-0 flex-col border-l border-slate-200 bg-white shadow-[-8px_0_20px_rgba(15,23,42,0.035)]`}>
      <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-slate-100 bg-slate-50 px-5">
        <div>
          <h2 className="text-[15px] font-bold text-slate-800">
            {panel === 'relationship' && '관계도'}
            {panel === 'reminder' && '요약'}
            {panel === 'settings' && '설정'}
            {panel === 'closed' && 'SpoKeeper'}
          </h2>
          <p className="text-xs font-semibold text-slate-400">현재 offset 기준으로 공개된 정보만 표시합니다.</p>
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
        {panel === 'closed' && (
          <div className="grid h-full place-items-center text-center text-sm font-medium leading-6 text-slate-400">
            상단 버튼으로 관계도, 요약, 설정을 열 수 있습니다.
          </div>
        )}
      </div>
    </aside>
  );
}
