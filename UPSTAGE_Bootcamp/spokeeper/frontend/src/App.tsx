import { Header } from './components/Header';
import { ReaderView } from './components/ReaderView';
import { Footer } from './components/Footer';
import { RelationshipPanel } from './components/RelationshipPanel';
import { ReminderPanel } from './components/ReminderPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { useSpoStore } from './store';

export default function App() {
  const panel = useSpoStore((s) => s.panel);

  return (
    <div className="flex h-full flex-col">
      <Header />
      <main className="flex-1 overflow-y-auto">
        <ReaderView />
      </main>
      <Footer />

      {panel === 'relationship' && <RelationshipPanel />}
      {panel === 'reminder' && <ReminderPanel />}
      {panel === 'settings' && <SettingsPanel />}
    </div>
  );
}
