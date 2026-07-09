// ── 관계도 패널 (F2): 빈/부분/전체 3상태 처리 ──────────────────
import { BOOK_ID } from '../lib/constants';
import { useGraph } from '../api/hooks';
import { useSpoStore } from '../store';
import { SlideOverPanel } from './SlideOverPanel';
import { RelationshipGraph } from './RelationshipGraph';
import { RelationshipList } from './RelationshipList';

export function RelationshipPanel() {
  const spoilerBoundary = useSpoStore((s) => s.spoilerBoundary);
  const spoilerSafe = useSpoStore((s) => s.spoilerSafe);
  const { data: graph, isLoading, isError } = useGraph(BOOK_ID, spoilerBoundary, spoilerSafe);

  const isEmpty = !!graph && graph.entities.length === 0;

  return (
    <SlideOverPanel title="관계도" subtitle="현재 읽은 위치까지의 관계">
      {/* 안내 배너 */}
      <div className="mb-4 rounded-xl border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs leading-5 text-indigo-700">
        현재 읽은 위치까지만 보여줘요. {spoilerSafe ? '아직 읽지 않은 내용은 숨겨집니다.' : '안심 모드 OFF — 전체 내용이 표시됩니다.'}
      </div>

      {isLoading && (
        <div className="space-y-3">
          <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
          <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600">
          관계도를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
        </div>
      )}

      {/* 빈 상태 */}
      {isEmpty && (
        <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-12 text-center">
          <div className="mb-2 text-3xl" aria-hidden>🌫️</div>
          <p className="text-sm font-medium text-slate-600">아직 공개된 인물이 없어요.</p>
          <p className="mt-1 text-xs text-slate-400">조금 더 읽으면 관계도가 채워집니다.</p>
        </div>
      )}

      {/* 부분/전체 상태 */}
      {graph && !isEmpty && (
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2">
            <RelationshipGraph graph={graph} />
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                관계 {graph.relationships.length}건 · 인물 {graph.entities.length}
              </h3>
            </div>
            <RelationshipList graph={graph} />
          </div>
        </div>
      )}
    </SlideOverPanel>
  );
}
