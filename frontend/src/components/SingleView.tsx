import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchPois, fetchScore, type PoiItem, type ScoreResponse } from "../api";
import MapView from "./MapView";
import MetricsPanel from "./MetricsPanel";
import RightPanel from "./RightPanel";

const DEFAULT_LAT = 33.595;
const DEFAULT_LON = -7.632;

import type { PoiFilterItem } from "./MetricsPanel";

function filterPoisByItem(
  pois: PoiItem[],
  filter: PoiFilterItem
): PoiItem[] {
  if (filter == null) return pois;
  const { section, value } = filter;
  switch (section) {
    case "category_density":
      return pois.filter((p) => p.super_category === value);
    case "nearest": {
      const inCategory = pois.filter((p) => p.super_category === value);
      if (inCategory.length === 0) return [];
      const minDist = Math.min(...inCategory.map((p) => p.distance_km));
      return inCategory.filter((p) => p.distance_km <= minDist + 1e-9);
    }
    case "accessibility":
      return pois.filter((p) => p.fclass === value);
    default:
      return pois;
  }
}

type Props = {
  pendingLocation?: { lat: number; lon: number } | null;
  onConsumePendingLocation?: () => void;
  onCoordDisplayChange?: (text: string, hasLocation: boolean) => void;
};

export default function SingleView({ pendingLocation, onConsumePendingLocation, onCoordDisplayChange }: Props) {
  const [lat, setLat] = useState(String(DEFAULT_LAT));
  const [lon, setLon] = useState(String(DEFAULT_LON));
  const [scoreData, setScoreData] = useState<ScoreResponse | null>(null);
  const [pois, setPois] = useState<PoiItem[]>([]);
  const [focusedPoiId, setFocusedPoiId] = useState<number | null>(null);
  const [poiFilter, setPoiFilter] = useState<PoiFilterItem>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredPois = useMemo(
    () => filterPoisByItem(pois, poiFilter),
    [pois, poiFilter]
  );

  const center: [number, number] | null =
    scoreData != null
      ? [scoreData.location.lat, scoreData.location.lon]
      : null;

  const runAnalysis = useCallback(async (latVal: number, lonVal: number) => {
    setError(null);
    setLoading(true);
    setPois([]);
    setPoiFilter(null);
    try {
      const res = await fetchScore(latVal, lonVal);
      setScoreData(res);
      setLat(latVal.toFixed(5));
      setLon(lonVal.toFixed(5));
      try {
        const poisList = await fetchPois(latVal, lonVal, 1);
        setPois(poisList);
      } catch {
        setPois([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRunFromInput = useCallback(() => {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (Number.isNaN(latNum) || Number.isNaN(lonNum)) {
      setError("Enter valid latitude and longitude.");
      return;
    }
    if (latNum < -90 || latNum > 90 || lonNum < -180 || lonNum > 180) {
      setError("Coordinates out of range.");
      return;
    }
    runAnalysis(latNum, lonNum);
  }, [lat, lon, runAnalysis]);

  const handleMapLocation = useCallback(
    (newLat: number, newLon: number) => {
      runAnalysis(newLat, newLon);
    },
    [runAnalysis]
  );

  useEffect(() => {
    if (scoreData) {
      const t = `${scoreData.location.lat.toFixed(5)}, ${scoreData.location.lon.toFixed(5)}`;
      onCoordDisplayChange?.(t, true);
    } else {
      onCoordDisplayChange?.("No location selected", false);
    }
  }, [scoreData, onCoordDisplayChange]);

  useEffect(() => {
    if (pendingLocation == null) return;
    const { lat, lon } = pendingLocation;
    runAnalysis(lat, lon);
    onConsumePendingLocation?.();
  }, [pendingLocation, onConsumePendingLocation, runAnalysis]);

  return (
    <>
      <div className="sidebar">
        <div className="input-section">
          <div className="section-label">Coordinates</div>
          <div className="coord-inputs">
            <div className="coord-field">
              <label htmlFor="lat-input">Latitude</label>
              <input
                id="lat-input"
                type="number"
                placeholder="33.5950"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
              />
            </div>
            <div className="coord-field">
              <label htmlFor="lon-input">Longitude</label>
              <input
                id="lon-input"
                type="number"
                placeholder="-7.6320"
                step="0.0001"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
              />
            </div>
          </div>
          {error && <div className="error-banner">{error}</div>}
          <button
            type="button"
            className="analyze-btn"
            onClick={handleRunFromInput}
            disabled={loading}
          >
            {loading ? "Computing…" : "Run"}
          </button>
        </div>
        <MetricsPanel
          data={scoreData}
          activeFilter={poiFilter}
          onItemClick={(section, value) =>
            setPoiFilter((prev) =>
              prev?.section === section && prev?.value === value ? null : { section, value }
            )
          }
          onClearFilter={() => setPoiFilter(null)}
        />
      </div>

      <div className="map-wrap" style={{ position: "relative", flex: 1, minHeight: 0 }}>
        <MapView
          center={center}
          pois={filteredPois}
          focusedPoiId={focusedPoiId}
          onFocusComplete={() => setFocusedPoiId(null)}
          onLocationSelect={handleMapLocation}
        />
        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <div className="loading-text">Computing spatial indicators…</div>
          </div>
        )}
      </div>

      <RightPanel data={scoreData} pois={filteredPois} onPoiClick={setFocusedPoiId} />
    </>
  );
}
