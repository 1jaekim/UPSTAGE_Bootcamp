import { useRef, useState, type ChangeEvent } from 'react';
import { useBook, useBooks, useUploadBook } from '../api/hooks';
import { useSpoStore, type PanelKind } from '../store';
import { SpoilerModeToggle } from './SpoilerModeToggle';

const TABS: Array<{ kind: Exclude<PanelKind, 'closed'>; label: string }> = [
  { kind: 'relationship', label: '관계도' },
  { kind: 'reminder', label: '요약' },
  { kind: 'settings', label: '설정' },
];

export function TopBar() {
  const selectedBookId = useSpoStore((s) => s.selectedBookId);
  const setSelectedBookId = useSpoStore((s) => s.setSelectedBookId);
  const panel = useSpoStore((s) => s.panel);
  const togglePanel = useSpoStore((s) => s.togglePanel);
  const { data: books } = useBooks();
  const { data: book } = useBook(selectedBookId);
  const uploadBook = useUploadBook();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    uploadBook.mutate(file, {
      onSuccess: (result) => setSelectedBookId(result.book_id),
      onError: (error) => setUploadError(error instanceof Error ? error.message : '업로드에 실패했습니다.'),
    });
  };

  return (
    <header className="z-30 flex min-w-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-4 shadow-[0_1px_2px_rgba(15,23,42,0.03)] backdrop-blur md:px-7">
      <div className="flex min-w-0 items-center gap-4">
        <div className="flex shrink-0 items-center gap-3">
          <div className="text-lg font-extrabold tracking-wide text-accent">SpoKeeper</div>
          <div className="hidden h-5 w-px bg-slate-200 sm:block" />
        </div>
        <select
          value={selectedBookId}
          onChange={(event) => setSelectedBookId(event.target.value)}
          className="hidden max-w-[280px] truncate rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 outline-none transition focus:border-accent md:block"
          aria-label="도서 선택"
        >
          {books?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
        <div className="min-w-0 truncate text-sm font-medium text-slate-500">
          {book ? `${book.title} · ${book.author}` : '책 정보를 불러오는 중'}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <SpoilerModeToggle />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploadBook.isPending}
          className="hidden h-9 items-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-bold text-slate-600 shadow-sm transition hover:border-accent hover:bg-indigo-50 hover:text-accent disabled:opacity-60 sm:inline-flex"
        >
          {uploadBook.isPending ? '업로드 중' : 'EPUB 업로드'}
        </button>
        <input ref={fileRef} type="file" accept=".epub" className="hidden" onChange={onFileChange} />
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.kind}
              type="button"
              onClick={() => togglePanel(tab.kind)}
              className={`h-9 rounded-lg border px-3 text-sm font-bold shadow-sm transition ${
                panel === tab.kind
                  ? 'border-accent bg-indigo-50 text-accent'
                  : 'border-slate-300 bg-white text-slate-600 hover:border-slate-400'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      {uploadError && (
        <div className="absolute right-7 top-14 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-600 shadow-sm">
          {uploadError}
        </div>
      )}
    </header>
  );
}
