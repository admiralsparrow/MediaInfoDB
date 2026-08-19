import { useState } from "react";
import FilterPanel from "./components/Filters/FilterPanel";
import FolderList from "./components/ScanStatus/FolderList";
import ScanBanner from "./components/ScanStatus/ScanBanner";
import HealthBanner from "./components/HealthBanner";
import MediaTable from "./components/MediaTable/MediaTable";
import QueuePage from "./components/Queue/QueuePage";
import LogsPage from "./components/Logs/LogsPage";

type View = "media" | "queue" | "logs";

function App() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [selectedLibraryId, setSelectedLibraryId] = useState<number | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null);
  const [view, setView] = useState<View>("media");

  const handleSelectLibrary = (id: number | null) => {
    setSelectedLibraryId(id);
    setSelectedFolderId(null);
    if (id !== null) setView("media");
  };

  const handleSelectFolder = (folderId: number | null) => {
    setSelectedFolderId(folderId);
    setView("media");
  };

  const activeFilters = (() => {
    const f = { ...filters };
    if (selectedLibraryId) f.library_id = String(selectedLibraryId);
    if (selectedFolderId) f.folder_id = String(selectedFolderId);
    return f;
  })();

  return (
    <div className="app">
      <header className="app-header">
        <h1><img src="/icon.svg" alt="" width="32" height="32" style={{ verticalAlign: 'middle', marginRight: '8px' }} />MediaInfoDB <span className="app-version">v{__APP_VERSION__}</span></h1>
        <nav className="app-nav">
          <button
            className={`nav-btn ${view === "media" ? "active" : ""}`}
            onClick={() => setView("media")}
          >
            Media
          </button>
          <button
            className={`nav-btn ${view === "queue" ? "active" : ""}`}
            onClick={() => setView("queue")}
          >
            Queue
          </button>
          <button
            className={`nav-btn ${view === "logs" ? "active" : ""}`}
            onClick={() => setView("logs")}
          >
            Logs
          </button>
        </nav>
      </header>

      <HealthBanner />
      <ScanBanner onNavigateToQueue={(folderId) => { setSelectedFolderId(folderId); setView("queue"); }} />

      {view === "media" ? (
        <div className="app-layout">
          <aside className="sidebar">
            <FolderList
              selectedLibraryId={selectedLibraryId}
              onSelectLibrary={handleSelectLibrary}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
            />
            <FilterPanel
              filters={filters}
              onChange={setFilters}
              libraryId={selectedLibraryId}
              onLoadQuery={(f, lib) => { setFilters(f); setSelectedLibraryId(lib); }}
            />
          </aside>

          <main className="main-content">
            <MediaTable filters={activeFilters} />
          </main>
        </div>
      ) : view === "queue" ? (
        <div className="app-layout">
          <aside className="sidebar">
            <FolderList
              selectedLibraryId={selectedLibraryId}
              onSelectLibrary={handleSelectLibrary}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
            />
          </aside>

          <main className="main-content">
            <QueuePage folderId={selectedFolderId} />
          </main>
        </div>
      ) : (
        <div className="app-layout">
          <aside className="sidebar">
            <FolderList
              selectedLibraryId={selectedLibraryId}
              onSelectLibrary={handleSelectLibrary}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
            />
          </aside>

          <main className="main-content">
            <LogsPage />
          </main>
        </div>
      )}
    </div>
  );
}

export default App;
