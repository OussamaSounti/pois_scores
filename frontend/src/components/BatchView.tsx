import { useCallback, useMemo, useState } from "react";
import { fetchBatch, BATCH_MAX, type BatchResult, type ScoreResponse } from "../api";

/** Build CSV string with full POI scores for each location (one row per location). */
function buildScoresCsv(results: BatchResult): string {
  if (results.length === 0) return "";

  const scalarKeys = [
    "lat",
    "lon",
    "poi_count_1km",
    "poi_count_400m",
    "n_categories",
    "n_poi_types",
    "entropy",
    "entropy_fclass",
    "aggregate_score",
  ] as const;

  const allCatKeys = new Set<string>();
  const allAccKeys = new Set<string>();
  const allNearestKeys = new Set<string>();
  for (const r of results) {
    Object.keys(r.scores.by_category ?? {}).forEach((k) => allCatKeys.add(k));
    Object.keys(r.scores.accessibility_400m ?? {}).forEach((k) => allAccKeys.add(k));
    Object.keys(r.scores.nearest_km ?? {}).forEach((k) => allNearestKeys.add(k));
  }
  const catKeys = [...allCatKeys].sort();
  const accKeys = [...allAccKeys].sort();
  const nearestKeys = [...allNearestKeys].sort();

  const escape = (v: string | number | boolean | null | undefined): string => {
    const s = v === null || v === undefined ? "" : String(v);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };

  const header =
    [
      "lat",
      "lon",
      ...scalarKeys.filter((k) => k !== "lat" && k !== "lon"),
      ...catKeys.map((k) => `category_${k}`),
      ...accKeys.map((k) => `acc_${k}`),
      ...nearestKeys.map((k) => `nearest_km_${k}`),
    ].join(",");

  const rows = results.map((r: ScoreResponse) => {
    const s = r.scores;
    const scalars: (string | number | null)[] = [
      r.location.lat,
      r.location.lon,
      s.poi_count_1km,
      s.poi_count_400m,
      s.n_categories,
      s.n_poi_types,
      s.entropy,
      s.entropy_fclass,
      s.aggregate_score ?? "",
    ];
    const catVals = catKeys.map((k) => s.by_category?.[k] ?? "");
    const accVals = accKeys.map((k) => (s.accessibility_400m?.[k] ? "1" : "0"));
    const nearestVals = nearestKeys.map((k) => s.nearest_km?.[k] ?? "");
    return [...scalars, ...catVals, ...accVals, ...nearestVals].map(escape).join(",");
  });

  return [header, ...rows].join("\r\n");
}

function downloadCsv(csv: string, filename: string) {
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function parseLocations(text: string): Array<{ lat: number; lon: number }> {
  const lines = text
    .trim()
    .split(/\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const out: Array<{ lat: number; lon: number }> = [];
  for (const line of lines) {
    const parts = line
      .split(/[\s,;]+/)
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length >= 2) {
      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      if (!Number.isNaN(lat) && !Number.isNaN(lon)) out.push({ lat, lon });
    }
  }
  return out;
}

export default function BatchView() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = useCallback(async () => {
    const locations = parseLocations(text);
    if (locations.length === 0) {
      setError("Enter at least one line with lat,lon (e.g. 33.595 -7.632).");
      return;
    }
    if (locations.length > BATCH_MAX) {
      setError(`Maximum ${BATCH_MAX} locations per request.`);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await fetchBatch(locations);
      setResults(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [text]);

  const handleExportCsv = useCallback(() => {
    if (!results || results.length === 0) return;
    const csv = buildScoresCsv(results);
    const filename = `batch_scores_${new Date().toISOString().slice(0, 10)}.csv`;
    downloadCsv(csv, filename);
  }, [results]);

  const canExport = useMemo(() => results != null && results.length > 0, [results]);

  return (
    <div className="batch-view">
      <div className="batch-input-section">
        <div className="section-label">Batch locations</div>
        <p className="batch-hint">
          One location per line: latitude and longitude (space or comma
          separated). Max {BATCH_MAX} locations.
        </p>
        <textarea
          className="batch-textarea"
          placeholder={"33.595 -7.632\n34.02 -6.83"}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {error && <div className="error-banner">{error}</div>}
        <button
          type="button"
          className="analyze-btn"
          onClick={handleRun}
          disabled={loading}
        >
          {loading ? "Computing…" : "Run batch"}
        </button>
      </div>
      <div className="batch-results">
        {results != null && (
          <>
            <div className="batch-results-toolbar">
              <button
                type="button"
                className="batch-export-btn"
                onClick={handleExportCsv}
                disabled={!canExport}
              >
                Export CSV
              </button>
            </div>
            <table className="batch-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Lat</th>
                <th>Lon</th>
                <th>POIs 1 km</th>
                <th>POIs 400 m</th>
                <th>Categories</th>
                <th>Aggregate</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{r.location.lat.toFixed(4)}</td>
                  <td>{r.location.lon.toFixed(4)}</td>
                  <td>{r.scores.poi_count_1km}</td>
                  <td>{r.scores.poi_count_400m}</td>
                  <td>{r.scores.n_categories}</td>
                  <td>
                    {r.scores.aggregate_score != null
                      ? r.scores.aggregate_score
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </>
        )}
      </div>
    </div>
  );
}
