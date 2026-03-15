import type { PoiItem, ScoreResponse } from '../api';

type Props = {
  data: ScoreResponse | null;
  pois?: PoiItem[];
  onPoiClick?: (poiId: number) => void;
};

export default function RightPanel({ data, pois = [], onPoiClick }: Props) {
  return (
    <div className="right-panel">
      <div className="poi-list-header">
        <div className="section-label">Nearby POIs</div>
        <div className="poi-count">
          {data ? `${pois.length} POIs within 1 km` : 'Select a location to begin'}
        </div>
      </div>
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {pois.length === 0 ? (
          <div className="poi-summary" style={{ padding: '20px 14px' }}>
            {data ? (
              <>No POIs in radius. Try another location.</>
            ) : (
              <>POIs within 1 km will appear here after selecting a location.</>
            )}
          </div>
        ) : (
          <ul className="poi-list">
            {pois.map((p) => (
              <li
                key={p.id}
                className="poi-item"
                role="button"
                tabIndex={0}
                onClick={() => onPoiClick?.(p.id)}
                onKeyDown={(e) => e.key === 'Enter' && onPoiClick?.(p.id)}
              >
                <div className="poi-item-name">{p.name || p.fclass}</div>
                <div className="poi-item-meta">
                  <span>{p.fclass}</span>
                  <span className="poi-item-dist">{p.distance_km.toFixed(2)} km</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
