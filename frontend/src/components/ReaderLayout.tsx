import { EpubJsReader } from './EpubJsReader';
import { SidePanel } from './SidePanel';

export function ReaderLayout() {
  return (
    <main className="grid min-h-0 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_minmax(420px,560px)]">
      <section className="relative min-h-0 overflow-hidden bg-[linear-gradient(90deg,#eef3f7,#f8fafc_18%,#f8fafc_82%,#eef3f7)] px-4 py-5 sm:px-8 lg:px-16 lg:py-8">
        <EpubJsReader />
      </section>
      <SidePanel />
    </main>
  );
}
