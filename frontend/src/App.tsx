import { useCallback, useState } from 'react';
import BatchView from './components/BatchView';
import PropertiesView from './components/PropertiesView';
import SingleView from './components/SingleView';

type Tab = 'single' | 'batch' | 'properties';

export default function App() {
  const [tab, setTab] = useState<Tab>('single');
  const [coordText, setCoordText] = useState('No location selected');
  const [hasLocation, setHasLocation] = useState(false);
  const [pendingSingleLocation, setPendingSingleLocation] = useState<{
    lat: number;
    lon: number;
    asOf?: string;
  } | null>(null);

  const goToSingleWithLocation = useCallback((lat: number, lon: number, asOf?: string) => {
    setPendingSingleLocation({ lat, lon, asOf });
    setTab('single');
  }, []);

  return (
    <>
      <header className="topbar">
        <div className="logo">
          Yakeey<span>Val</span>
        </div>
        <div className="topbar-div" />
        <div className="topbar-sub">Morocco</div>
        <div
          className={`coord-display ${hasLocation ? 'active' : ''}`}
          style={{ visibility: tab === 'single' ? 'visible' : 'hidden' }}
        >
          <div className="status-dot" />
          <span className="coord-text">{coordText}</span>
        </div>
      </header>

      <div className="tabs">
        <button
          type="button"
          className={`tab ${tab === 'single' ? 'active' : ''}`}
          onClick={() => setTab('single')}
        >
          Single
        </button>
        <button
          type="button"
          className={`tab ${tab === 'batch' ? 'active' : ''}`}
          onClick={() => setTab('batch')}
        >
          Batch
        </button>
        <button
          type="button"
          className={`tab ${tab === 'properties' ? 'active' : ''}`}
          onClick={() => setTab('properties')}
        >
          Properties
        </button>
      </div>

      <div className="main" style={{ display: tab === 'single' ? 'flex' : 'none' }}>
        <SingleView
          pendingLocation={pendingSingleLocation}
          onConsumePendingLocation={() => setPendingSingleLocation(null)}
          onCoordDisplayChange={(text, active) => {
            setCoordText(text);
            setHasLocation(active);
          }}
        />
      </div>
      <div className="main" style={{ display: tab === 'batch' ? 'flex' : 'none' }}>
        <BatchView onRowClick={goToSingleWithLocation} />
      </div>
      <div className="main" style={{ display: tab === 'properties' ? 'flex' : 'none' }}>
        <PropertiesView onGoToSingle={goToSingleWithLocation} />
      </div>
    </>
  );
}
