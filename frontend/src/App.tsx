import { ProgressFooter } from './components/ProgressFooter';
import { ReaderLayout } from './components/ReaderLayout';
import { TopBar } from './components/TopBar';

export default function App() {
  return (
    <div className="grid h-full grid-rows-[60px_minmax(0,1fr)_72px] bg-[#eef3f7] text-slate-800">
      <TopBar />
      <ReaderLayout />
      <ProgressFooter />
    </div>
  );
}
