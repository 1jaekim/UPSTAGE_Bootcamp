// ── 설정 패널 (F3): 이름 마스킹 · 안심 모드 · 소스 표시 ─────────
import { IS_MOCK } from '../api/client';
import { useSpoStore } from '../store';
import { SlideOverPanel } from './SlideOverPanel';

function Row({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <span>
        <span className="block text-sm font-medium text-slate-700">{label}</span>
        <span className="mt-0.5 block text-xs text-slate-400">{desc}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition ${
          checked ? 'bg-accent' : 'bg-slate-200'
        }`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${
            checked ? 'translate-x-5' : 'translate-x-0.5'
          }`}
        />
      </button>
    </label>
  );
}

export function SettingsPanel() {
  const spoilerSafe = useSpoStore((s) => s.spoilerSafe);
  const setSpoilerSafe = useSpoStore((s) => s.setSpoilerSafe);
  const maskNames = useSpoStore((s) => s.maskNames);
  const setMaskNames = useSpoStore((s) => s.setMaskNames);

  return (
    <SlideOverPanel title="설정" subtitle="표시 · 스포일러 옵션">
      <div className="space-y-3">
        <Row
          label="안심 모드"
          desc="켜면 아직 읽지 않은 내용은 요청하거나 표시하지 않습니다."
          checked={spoilerSafe}
          onChange={setSpoilerSafe}
        />
        <Row
          label="이름 마스킹"
          desc="관계도/리스트의 인물 이름을 첫 글자만 남기고 가립니다."
          checked={maskNames}
          onChange={setMaskNames}
        />

        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
          <div className="flex items-center justify-between">
            <span>데이터 소스</span>
            <span
              className={`rounded-full px-2 py-0.5 font-medium ${
                IS_MOCK ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
              }`}
            >
              {IS_MOCK ? 'MOCK 픽스처' : '실서버 (FastAPI)'}
            </span>
          </div>
          <p className="mt-1.5 leading-5 text-slate-400">
            같은 화면에서 테스트 데이터와 실제 서버 데이터를 바꿔 볼 수 있습니다.
          </p>
        </div>
      </div>
    </SlideOverPanel>
  );
}
