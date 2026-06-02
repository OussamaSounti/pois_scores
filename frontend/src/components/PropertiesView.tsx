import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import type { LatLngBounds } from 'leaflet';
import L from 'leaflet';
import {
  fetchPropertyDetail,
  fetchPropertiesMap,
  fetchPropertyStats,
  type PropertyLevel,
  type PropertyMapItem,
  type PropertyStatsGroup,
  type PropertiesFilters,
} from '../api';

import districtsGeo from '../districts.geojson.json';
import neighbourhoodsGeo from '../neighbourhoods.geojson.json';
import irisGeo from '../iris.geojson.json';
import ilotsGeo from '../ilots.geojson.json';

const MOROCCO_CENTER: [number, number] = [31.7917, -7.0926];
const MOROCCO_ZOOM = 7;
const CARTO_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const CARTO_ATTR = '© OpenStreetMap © Carto';

type MetricKey = 'aggregate_score' | 'entropy' | 'poi_count_1km';

type BoundsBox = { west: number; south: number; east: number; north: number };

/** Invalidate map size when the container becomes visible (fixes grey tiles on tab switch). */
function InvalidateSizeOnVisible() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      map.invalidateSize();
    });
    const container = map.getContainer();
    observer.observe(container);
    map.invalidateSize();
    return () => observer.disconnect();
  }, [map]);
  return null;
}

/** Create a custom pane below the default overlayPane so polygons don't steal clicks from markers. */
function EnsureHierarchyPane() {
  const map = useMap();
  useEffect(() => {
    if (!map.getPane('hierarchy')) {
      const pane = map.createPane('hierarchy');
      pane.style.zIndex = '350'; // below overlayPane (400) where CircleMarkers render
      pane.style.pointerEvents = 'auto';
    }
  }, [map]);
  return null;
}

/** Fit the map view to the relevant hierarchy polygons when filters change. */
function FitToHierarchy({
  districtUid,
  neighbourhoodUid,
  irisUid,
  ilotUid,
}: {
  districtUid: string;
  neighbourhoodUid: string;
  irisUid: string;
  ilotUid: string;
}) {
  const map = useMap();
  const fittedKeyRef = useRef('');

  useEffect(() => {
    // Determine which GeoJSON features to fit to
    let features: GeoJSON.Feature[];
    if (ilotUid) {
      features = (ilotsGeo as GeoJSON.FeatureCollection).features.filter(
        (f) => (f.properties as Record<string, unknown>)?.uid === ilotUid
      );
    } else if (irisUid) {
      features = (ilotsGeo as GeoJSON.FeatureCollection).features.filter(
        (f) => (f.properties as Record<string, unknown>)?.iris_uid === irisUid
      );
    } else if (neighbourhoodUid) {
      features = (irisGeo as GeoJSON.FeatureCollection).features.filter(
        (f) => (f.properties as Record<string, unknown>)?.neighbourhood_uid === neighbourhoodUid
      );
    } else if (districtUid) {
      features = (neighbourhoodsGeo as GeoJSON.FeatureCollection).features.filter(
        (f) => (f.properties as Record<string, unknown>)?.district_uid === districtUid
      );
    } else {
      features = (districtsGeo as GeoJSON.FeatureCollection).features;
    }

    const key = `${districtUid}|${neighbourhoodUid}|${irisUid}|${ilotUid}`;
    if (key === fittedKeyRef.current) return;
    fittedKeyRef.current = key;

    if (features.length === 0) return;
    const geoLayer = L.geoJSON({ type: 'FeatureCollection', features } as GeoJSON.FeatureCollection);
    const bounds = geoLayer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 16, animate: true });
    }
  }, [districtUid, neighbourhoodUid, irisUid, ilotUid, map]);

  return null;
}

function BoundsReporter({
  onBounds,
}: {
  onBounds: (bbox: BoundsBox) => void;
}) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const report = useCallback(
    (bounds: LatLngBounds) => {
      const sw = bounds.getSouthWest();
      const ne = bounds.getNorthEast();
      // Debounce to avoid firing on every micro-pan
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        onBounds({ west: sw.lng, south: sw.lat, east: ne.lng, north: ne.lat });
      }, 300);
    },
    [onBounds]
  );

  const map = useMapEvents({
    moveend: () => report(map.getBounds()),
    zoomend: () => report(map.getBounds()),
  });

  useEffect(() => {
    report(map.getBounds());
  }, [map, report]);

  return null;
}

function metricValue(item: PropertyMapItem, metric: MetricKey): number | null {
  if (metric === 'aggregate_score') return item.scores.aggregate_score;
  if (metric === 'entropy') return item.scores.entropy;
  return item.scores.poi_count_1km;
}

function markerColor(item: PropertyMapItem, metric: MetricKey): string {
  const value = metricValue(item, metric);
  if (value == null) return '#8a93b2';
  if (metric === 'aggregate_score') {
    if (value >= 70) return '#1e9d65';
    if (value >= 40) return '#f5a524';
    return '#d64545';
  }
  if (metric === 'entropy') {
    if (value >= 2.2) return '#1a7fa8';
    if (value >= 1.3) return '#f5a524';
    return '#d64545';
  }
  if (value >= 40) return '#1e9d65';
  if (value >= 15) return '#f5a524';
  return '#d64545';
}

function levelLabel(level: PropertyLevel): string {
  if (level === 'district') return 'District';
  if (level === 'neighbourhood') return 'Neighbourhood';
  if (level === 'iris') return 'IRIS';
  return 'Ilot';
}

const LEVEL_COLORS: Record<string, string> = {
  district: '#29c25c',
  neighbourhood: '#1a7fa8',
  iris: '#a855f7',
  ilot: '#f59e0b',
};

/**
 * Renders the appropriate polygon layer based on hierarchy selection.
 * Shows the deepest selected level's children, or districts when nothing is selected.
 */
function HierarchyPolygons({
  districtUid,
  neighbourhoodUid,
  irisUid,
  ilotUid,
}: {
  districtUid: string;
  neighbourhoodUid: string;
  irisUid: string;
  ilotUid: string;
}) {
  // Determine which layer to show: always show the *next* level down from current selection,
  // or the selected level itself if it's the deepest.
  const { data, level, filterKey, filterValue } = useMemo(() => {
    if (ilotUid) {
      // Show just the selected ilot
      return {
        data: ilotsGeo as GeoJSON.FeatureCollection,
        level: 'ilot',
        filterKey: 'uid',
        filterValue: ilotUid,
      };
    }
    if (irisUid) {
      // Show ilots within this IRIS
      return {
        data: ilotsGeo as GeoJSON.FeatureCollection,
        level: 'ilot',
        filterKey: 'iris_uid',
        filterValue: irisUid,
      };
    }
    if (neighbourhoodUid) {
      // Show IRIS zones within this neighbourhood
      return {
        data: irisGeo as GeoJSON.FeatureCollection,
        level: 'iris',
        filterKey: 'neighbourhood_uid',
        filterValue: neighbourhoodUid,
      };
    }
    if (districtUid) {
      // Show neighbourhoods within this district
      return {
        data: neighbourhoodsGeo as GeoJSON.FeatureCollection,
        level: 'neighbourhood',
        filterKey: 'district_uid',
        filterValue: districtUid,
      };
    }
    // No selection → show all districts
    return {
      data: districtsGeo as GeoJSON.FeatureCollection,
      level: 'district',
      filterKey: null,
      filterValue: null,
    };
  }, [districtUid, neighbourhoodUid, irisUid, ilotUid]);

  const filtered = useMemo(() => {
    if (!filterKey || !filterValue) return data;
    return {
      ...data,
      features: data.features.filter(
        (f) => (f.properties as Record<string, unknown>)?.[filterKey] === filterValue
      ),
    };
  }, [data, filterKey, filterValue]);

  const color = LEVEL_COLORS[level] ?? '#8a93b2';

  // key forces GeoJSON component to re-mount when data changes (react-leaflet caches)
  const geoKey = `${level}-${filterValue ?? 'all'}`;

  return (
    <GeoJSON
      key={geoKey}
      data={filtered}
      pane="hierarchy"
      style={() => ({
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: 0.10,
        dashArray: level === 'district' ? undefined : '4 4',
      })}
      onEachFeature={(feature, layer) => {
        const label = (feature.properties as Record<string, unknown>)?.label;
        if (label) {
          layer.bindTooltip(String(label), { sticky: true, className: 'hierarchy-tooltip' });
        }
      }}
    />
  );
}

export default function PropertiesView({
  onGoToSingle,
}: {
  onGoToSingle?: (lat: number, lon: number, asOf?: string) => void;
}) {
  const [bbox, setBbox] = useState<BoundsBox | null>(null);
  const [metric, setMetric] = useState<MetricKey>('aggregate_score');

  const [districtUid, setDistrictUid] = useState('');
  const [neighbourhoodUid, setNeighbourhoodUid] = useState('');
  const [irisUid, setIrisUid] = useState('');
  const [ilotUid, setIlotUid] = useState('');

  const [districtGroups, setDistrictGroups] = useState<PropertyStatsGroup[]>([]);
  const [neighbourhoodGroups, setNeighbourhoodGroups] = useState<PropertyStatsGroup[]>([]);
  const [irisGroups, setIrisGroups] = useState<PropertyStatsGroup[]>([]);
  const [ilotGroups, setIlotGroups] = useState<PropertyStatsGroup[]>([]);

  const [items, setItems] = useState<PropertyMapItem[]>([]);
  const [count, setCount] = useState(0);
  const [selected, setSelected] = useState<PropertyMapItem | null>(null);
  const [loadingMap, setLoadingMap] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filters: PropertiesFilters = useMemo(() => {
    const out: PropertiesFilters = {};
    if (districtUid) out.district_uid = districtUid;
    if (neighbourhoodUid) out.neighbourhood_uid = neighbourhoodUid;
    if (irisUid) out.iris_uid = irisUid;
    if (ilotUid) out.ilot_uid = ilotUid;
    return out;
  }, [districtUid, neighbourhoodUid, irisUid, ilotUid]);

  const currentStatsLevel: PropertyLevel =
    ilotUid !== ''
      ? 'ilot'
      : irisUid !== ''
        ? 'iris'
        : neighbourhoodUid !== ''
          ? 'neighbourhood'
          : 'district';

  const currentStatsGroups =
    currentStatsLevel === 'district'
      ? districtGroups
      : currentStatsLevel === 'neighbourhood'
        ? neighbourhoodGroups
        : currentStatsLevel === 'iris'
          ? irisGroups
          : ilotGroups;

  useEffect(() => {
    fetchPropertyStats('district')
      .then(setDistrictGroups)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load districts'));
  }, []);

  useEffect(() => {
    if (!districtUid) {
      setNeighbourhoodGroups([]);
      setNeighbourhoodUid('');
      return;
    }
    fetchPropertyStats('neighbourhood', { district_uid: districtUid })
      .then(setNeighbourhoodGroups)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load neighbourhoods'));
  }, [districtUid]);

  useEffect(() => {
    if (!neighbourhoodUid) {
      setIrisGroups([]);
      setIrisUid('');
      return;
    }
    fetchPropertyStats('iris', {
      district_uid: districtUid || undefined,
      neighbourhood_uid: neighbourhoodUid,
    })
      .then(setIrisGroups)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load IRIS zones'));
  }, [districtUid, neighbourhoodUid]);

  useEffect(() => {
    if (!irisUid) {
      setIlotGroups([]);
      setIlotUid('');
      return;
    }
    fetchPropertyStats('ilot', {
      district_uid: districtUid || undefined,
      neighbourhood_uid: neighbourhoodUid || undefined,
      iris_uid: irisUid,
    })
      .then(setIlotGroups)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load ilots'));
  }, [districtUid, neighbourhoodUid, irisUid]);

  useEffect(() => {
    if (!bbox) return;
    setLoadingMap(true);
    fetchPropertiesMap(bbox, filters)
      .then((res) => {
        setItems(res.items);
        setCount(res.count);
        setError(null);
        setSelected((prev) => (prev ? (res.items.find((x) => x.id === prev.id) ?? prev) : null));
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Failed to load properties');
        setItems([]);
        setCount(0);
      })
      .finally(() => setLoadingMap(false));
  }, [bbox, filters]);

  const onSelectProperty = useCallback((propertyId: number) => {
    fetchPropertyDetail(propertyId)
      .then((item) => {
        setSelected(item);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load property detail'));
  }, []);

  return (
    <>
      <div className="sidebar">
        <div className="input-section">
          <div className="section-label">Properties Explorer</div>
          <p className="batch-hint" style={{ marginBottom: 10 }}>
            Visualize loaded properties and inspect detailed POI feature scores by hierarchy.
          </p>

          <div className="coord-field" style={{ marginBottom: 8 }}>
            <label htmlFor="metric-select">Map color metric</label>
            <select
              id="metric-select"
              className="properties-select"
              value={metric}
              onChange={(e) => setMetric(e.target.value as MetricKey)}
            >
              <option value="aggregate_score">Aggregate score</option>
              <option value="entropy">Entropy (category diversity)</option>
              <option value="poi_count_1km">POI count (1 km)</option>
            </select>
          </div>

          <div className="coord-field" style={{ marginBottom: 8 }}>
            <label htmlFor="district-select">District</label>
            <select
              id="district-select"
              className="properties-select"
              value={districtUid}
              onChange={(e) => {
                setDistrictUid(e.target.value);
                setNeighbourhoodUid('');
                setIrisUid('');
                setIlotUid('');
              }}
            >
              <option value="">All districts</option>
              {districtGroups.map((g) => (
                <option key={g.key} value={g.key}>
                  {g.label} ({g.properties_count})
                </option>
              ))}
            </select>
          </div>

          <div className="coord-field" style={{ marginBottom: 8 }}>
            <label htmlFor="neighbourhood-select">Neighbourhood</label>
            <select
              id="neighbourhood-select"
              className="properties-select"
              value={neighbourhoodUid}
              onChange={(e) => {
                setNeighbourhoodUid(e.target.value);
                setIrisUid('');
                setIlotUid('');
              }}
              disabled={!districtUid}
            >
              <option value="">All neighbourhoods</option>
              {neighbourhoodGroups.map((g) => (
                <option key={g.key} value={g.key}>
                  {g.label} ({g.properties_count})
                </option>
              ))}
            </select>
          </div>

          <div className="coord-field" style={{ marginBottom: 8 }}>
            <label htmlFor="iris-select">IRIS zone</label>
            <select
              id="iris-select"
              className="properties-select"
              value={irisUid}
              onChange={(e) => {
                setIrisUid(e.target.value);
                setIlotUid('');
              }}
              disabled={!neighbourhoodUid}
            >
              <option value="">All IRIS zones</option>
              {irisGroups.map((g) => (
                <option key={g.key} value={g.key}>
                  {g.label} ({g.properties_count})
                </option>
              ))}
            </select>
          </div>

          <div className="coord-field">
            <label htmlFor="ilot-select">Ilot (block)</label>
            <select
              id="ilot-select"
              className="properties-select"
              value={ilotUid}
              onChange={(e) => setIlotUid(e.target.value)}
              disabled={!irisUid}
            >
              <option value="">All ilots</option>
              {ilotGroups.map((g) => (
                <option key={g.key} value={g.key}>
                  {g.label} ({g.properties_count})
                </option>
              ))}
            </select>
          </div>

          <p className="batch-hint" style={{ marginTop: 10, marginBottom: 0 }}>
            Visible properties in map window: {count}
          </p>
          {error && <div className="error-banner" style={{ marginTop: 10 }}>{error}</div>}
        </div>

        <div className="metrics-panel">
          <div className="metric-group" style={{ animationDelay: '0s' }}>
            <div className="metric-group-title">{levelLabel(currentStatsLevel)} stats</div>
            {currentStatsGroups.length === 0 ? (
              <div className="poi-summary">No grouped stats for this selection.</div>
            ) : (
              currentStatsGroups.slice(0, 12).map((g) => (
                <div key={`${currentStatsLevel}-${g.key}`} className="nearest-row">
                  <div className="nearest-name">{g.label}</div>
                  <div className="nearest-dist">{g.properties_count} props</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="map-wrap" style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <MapContainer
          center={MOROCCO_CENTER}
          zoom={MOROCCO_ZOOM}
          style={{ height: '100%', width: '100%', minHeight: 300 }}
          zoomControl
        >
          <TileLayer url={CARTO_URL} attribution={CARTO_ATTR} maxZoom={19} />
          <InvalidateSizeOnVisible />
          <EnsureHierarchyPane />
          <BoundsReporter onBounds={setBbox} />
          <FitToHierarchy
            districtUid={districtUid}
            neighbourhoodUid={neighbourhoodUid}
            irisUid={irisUid}
            ilotUid={ilotUid}
          />
          <HierarchyPolygons
            districtUid={districtUid}
            neighbourhoodUid={neighbourhoodUid}
            irisUid={irisUid}
            ilotUid={ilotUid}
          />
          {items.map((item) => (
            <CircleMarker
              key={item.id}
              center={[item.latitude, item.longitude]}
              radius={5}
              pathOptions={{ color: markerColor(item, metric), fillOpacity: 0.75, weight: 1 }}
              eventHandlers={{
                click: () => onSelectProperty(item.id),
                dblclick: () =>
                  onGoToSingle?.(
                    item.latitude,
                    item.longitude,
                    item.transaction_date?.slice(0, 10) ?? undefined
                  ),
              }}
            >
              <Popup maxWidth={260}>
                <div className="popup-name">Property #{item.id}</div>
                <div className="popup-meta">
                  {item.asset_type ?? 'Unknown type'}
                  <br />
                  Price: {item.asset_price != null ? item.asset_price.toLocaleString() : 'n/a'} MAD
                  <br />
                  POIs (1 km): {item.scores.poi_count_1km ?? 'n/a'}
                  <br />
                  Entropy: {item.scores.entropy != null ? item.scores.entropy.toFixed(3) : 'n/a'}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
        {loadingMap && (
          <div className="loading-overlay">
            <div className="spinner" />
            <div className="loading-text">Loading properties…</div>
          </div>
        )}
      </div>

      <div className="right-panel">
        <div className="poi-list-header">
          <div className="section-label">Property Detail</div>
          <div className="poi-count">
            {selected ? `Property #${selected.id}` : 'Click a property marker'}
          </div>
        </div>
        <div className="metrics-panel" style={{ paddingTop: 10 }}>
          {!selected ? (
            <div className="poi-summary">Select a property to inspect non-aggregated score fields.</div>
          ) : (
            <>
              <div className="metric-group" style={{ animationDelay: '0s' }}>
                <div className="metric-group-title">Location hierarchy</div>
                <div className="nearest-row">
                  <div className="nearest-name">District</div>
                  <div className="nearest-dist">{selected.district_name ?? 'n/a'}</div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">Neighbourhood</div>
                  <div className="nearest-dist">{selected.neighbour_name ?? 'n/a'}</div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">IRIS</div>
                  <div className="nearest-dist">{selected.iris_code ?? 'n/a'}</div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">Ilot</div>
                  <div className="nearest-dist">{selected.ilot_objectid ?? 'n/a'}</div>
                </div>
              </div>

              <div className="metric-group" style={{ animationDelay: '0.07s' }}>
                <div className="metric-group-title">Scores (non-aggregated)</div>
                <div className="nearest-row">
                  <div className="nearest-name">POI snapshot</div>
                  <div className="nearest-dist">
                    {selected.scores.transaction_date ?? 'current'}
                  </div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">POI source</div>
                  <div className="nearest-dist">
                    {selected.scores.poi_source ?? 'n/a'}
                  </div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">POIs (1 km)</div>
                  <div className="nearest-dist">{selected.scores.poi_count_1km ?? 'n/a'}</div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">POIs (400 m)</div>
                  <div className="nearest-dist">{selected.scores.poi_count_400m ?? 'n/a'}</div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">Entropy</div>
                  <div className="nearest-dist">
                    {selected.scores.entropy != null ? selected.scores.entropy.toFixed(3) : 'n/a'}
                  </div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">Entropy (type)</div>
                  <div className="nearest-dist">
                    {selected.scores.entropy_fclass != null
                      ? selected.scores.entropy_fclass.toFixed(3)
                      : 'n/a'}
                  </div>
                </div>
                <div className="nearest-row">
                  <div className="nearest-name">Aggregate</div>
                  <div className="nearest-dist">
                    {selected.scores.aggregate_score != null
                      ? selected.scores.aggregate_score.toFixed(1)
                      : 'n/a'}
                  </div>
                </div>
              </div>

              <div className="metric-group" style={{ animationDelay: '0.14s' }}>
                <div className="metric-group-title">By category</div>
                {Object.keys(selected.scores.by_category).length === 0 ? (
                  <div className="poi-summary">No category payload available.</div>
                ) : (
                  Object.entries(selected.scores.by_category)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([k, v]) => (
                      <div key={k} className="nearest-row">
                        <div className="nearest-name">{k}</div>
                        <div className="nearest-dist">{v}</div>
                      </div>
                    ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
