import { useEffect, useRef, useState } from 'react';
import { Circle, GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { FeatureCollection } from 'geojson';
import type { PoiItem } from '../api';
import { CAT_COLORS } from '../constants';

const MOROCCO_CENTER: [number, number] = [31.7917, -7.0926];
const MOROCCO_ZOOM = 6;
const LOCATION_ZOOM = 15;
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** Re-centres only when the coordinates actually change (not on every parent render). */
function SetView({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  const [lat, lon] = center;
  useEffect(() => {
    map.setView([lat, lon], zoom);
  }, [map, lat, lon, zoom]);
  return null;
}

/** Keeps Leaflet's internal size in sync when the container resizes (e.g. side panels appearing). */
function ResizeHandler() {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    const ro = new ResizeObserver(() => map.invalidateSize({ animate: false }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);
  return null;
}

/** Only double-click triggers analysis; single-click is ignored. Uses map.on('dblclick') so click never runs. */
function DblClickHandler({ onLocation }: { onLocation: (lat: number, lon: number) => void }) {
  const map = useMap();
  useEffect(() => {
    const handler = (e: L.LeafletMouseEvent) => {
      onLocation(e.latlng.lat, e.latlng.lng);
    };
    map.on('dblclick', handler);
    return () => {
      map.off('dblclick', handler);
    };
  }, [map, onLocation]);
  return null;
}

function CenterMarker({ lat, lon }: { lat: number; lon: number }) {
  const icon = L.divIcon({
    html: `<div style="width:14px;height:14px;border-radius:50%;background:#c2622a;border:2.5px solid #fff;box-shadow:0 2px 10px rgba(194,98,42,0.5)"></div>`,
    className: '',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
  return <Marker position={[lat, lon]} icon={icon} />;
}

function poiIconForCategory(superCategory: string) {
  const color = CAT_COLORS[superCategory] ?? '#8a93b2';
  return L.divIcon({
    html: `<div style="width:11px;height:11px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,0.25),0 1px 4px rgba(0,0,0,0.35)"></div>`,
    className: '',
    iconSize: [11, 11],
    iconAnchor: [5, 5],
  });
}

const FOCUS_ZOOM = 18;
const FLY_DURATION = 0.5;
const POPUP_DELAY_MS = 550;

/** Flies to a POI and opens its popup when focusedPoiId is set. Must be inside MapContainer. */
function FlyToPoi({
  pois,
  focusedPoiId,
  onFocusComplete,
  markerRefs,
}: {
  pois: PoiItem[];
  focusedPoiId: string | null;
  onFocusComplete: () => void;
  markerRefs: React.MutableRefObject<Record<string, L.Marker | null>>;
}) {
  const map = useMap();
  useEffect(() => {
    if (focusedPoiId == null || pois.length === 0) return;
    const poi = pois.find((p) => p.id === focusedPoiId);
    if (!poi) return;
    map.flyTo([poi.latitude, poi.longitude], FOCUS_ZOOM, {
      animate: true,
      duration: FLY_DURATION,
    });
    const t = setTimeout(() => {
      const marker = markerRefs.current[focusedPoiId];
      if (marker) marker.openPopup();
      onFocusComplete();
    }, POPUP_DELAY_MS);
    return () => clearTimeout(t);
  }, [focusedPoiId, map, onFocusComplete, pois, markerRefs]);
  return null;
}

type Props = {
  center: [number, number] | null;
  pois: PoiItem[];
  focusedPoiId?: string | null;
  onFocusComplete?: () => void;
  onLocationSelect: (lat: number, lon: number) => void;
};

export default function MapView({
  center,
  pois = [],
  focusedPoiId = null,
  onFocusComplete,
  onLocationSelect,
}: Props) {
  const mapCenter = center ?? MOROCCO_CENTER;
  const mapZoom = center ? LOCATION_ZOOM : MOROCCO_ZOOM;
  const markerRefs = useRef<Record<string, L.Marker | null>>({});
  const [showCoastline, setShowCoastline] = useState(false);
  const [coastlineGeo, setCoastlineGeo] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    if (showCoastline && !coastlineGeo) {
      fetch('/api/v1/geo/coastline')
        .then((r) => r.json())
        .then(setCoastlineGeo)
        .catch(console.error);
    }
  }, [showCoastline, coastlineGeo]);

  return (
    <div className="map-wrap">
      <div className="map-inner">
        {/* Geo overlay toggles */}
        <div className="geo-overlay-btns">
          <button
            className={`geo-toggle-btn${showCoastline ? ' active' : ''}`}
            onClick={() => setShowCoastline((v) => !v)}
            title="Toggle coastline segments (geo.coastline)"
          >
            Coastline
          </button>
        </div>
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '100%', width: '100%', minHeight: 300 }}
          zoomControl
          doubleClickZoom={false}
        >
          <ResizeHandler />
          {center && <SetView center={center} zoom={LOCATION_ZOOM} />}
          <TileLayer url={TILE_URL} attribution={TILE_ATTR} maxZoom={19} />
          <DblClickHandler onLocation={onLocationSelect} />
          {/* Geo verification layers */}
          {showCoastline && coastlineGeo && (
            <GeoJSON
              key="coastline"
              data={coastlineGeo}
              style={{ color: '#1a7fa8', weight: 2.5, fillOpacity: 0 }}
            />
          )}
          {center && (
            <>
              <Circle
                center={center}
                radius={1000}
                pathOptions={{
                  color: '#c2622a',
                  weight: 1.5,
                  fillColor: '#c2622a',
                  fillOpacity: 0.04,
                  dashArray: '5 5',
                }}
              />
              <Circle
                center={center}
                radius={400}
                pathOptions={{
                  color: '#1a7fa8',
                  weight: 1.5,
                  fillColor: '#1a7fa8',
                  fillOpacity: 0.07,
                }}
              />
              <CenterMarker lat={center[0]} lon={center[1]} />
              {pois.map((p) => (
                <Marker
                  key={p.id}
                  position={[p.latitude, p.longitude]}
                  icon={poiIconForCategory(p.super_category)}
                  ref={(r) => {
                    markerRefs.current[p.id] = r != null ? (r as unknown as L.Marker) : null;
                  }}
                >
                  <Popup maxWidth={220}>
                    <div className="popup-name">{p.name || p.fclass}</div>
                    <div className="popup-meta">
                      {p.fclass} · {p.super_category}
                      <br />
                      <span className="popup-dist">{p.distance_km.toFixed(2)} km away</span>
                    </div>
                  </Popup>
                </Marker>
              ))}
              <FlyToPoi
                pois={pois}
                focusedPoiId={focusedPoiId}
                onFocusComplete={onFocusComplete ?? (() => {})}
                markerRefs={markerRefs}
              />
            </>
          )}
        </MapContainer>
      </div>
      <div className="map-hint" style={{ opacity: center ? 0 : 1 }}>
        Double‑click on the map to analyze that location
      </div>
    </div>
  );
}
