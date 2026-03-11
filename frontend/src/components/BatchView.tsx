import { useCallback, useMemo, useRef, useState } from "react";
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

/** Match numbers (including negative and decimal) in a string */
const NUMBER_REGEX = /[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/g;

function isHeaderLine(line: string): boolean {
  const lower = line.trim().toLowerCase();
  if (!lower) return false;
  const headerWords = ["lat", "lon", "latitude", "longitude", "y", "x"];
  const tokens = lower.split(/[\s,\t;|]+/).filter(Boolean);
  return tokens.length >= 2 && tokens.every((t) => headerWords.some((w) => t.startsWith(w) || t === w));
}

function parseLocations(text: string): Array<{ lat: number; lon: number }> {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#") && !l.startsWith("//"));
  const out: Array<{ lat: number; lon: number }> = [];
  const seenFirstLine = { value: false };
  for (const line of lines) {
    if (!seenFirstLine.value && isHeaderLine(line)) {
      seenFirstLine.value = true;
      continue;
    }
    seenFirstLine.value = true;
    const numStrs = line.match(NUMBER_REGEX) ?? [];
    if (numStrs.length >= 2) {
      const a = parseFloat(numStrs[0]);
      const b = parseFloat(numStrs[1]);
      if (Number.isNaN(a) || Number.isNaN(b)) continue;
      const inLatRange = (n: number) => n >= -90 && n <= 90;
      const inLonRange = (n: number) => n >= -180 && n <= 180;
      let lat: number;
      let lon: number;
      if (inLatRange(a) && inLonRange(b)) {
        lat = a;
        lon = b;
      } else if (inLonRange(a) && inLatRange(b)) {
        lat = b;
        lon = a;
      } else {
        lat = a;
        lon = b;
      }
      if (inLatRange(lat) && inLonRange(lon)) out.push({ lat, lon });
    }
  }
  return out;
}

type LocationPair = { lat: number; lon: number };

function locationsToText(locations: LocationPair[]): string {
  return locations.map(({ lat, lon }) => `${lat} ${lon}`).join("\n");
}

/** Parse CSV text; detect lat/lon columns by header or use first two numeric columns. */
function parseLocationsFromCsv(csvText: string): LocationPair[] {
  const lines = csvText.trim().split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length === 0) return [];
  const inLatRange = (n: number) => n >= -90 && n <= 90;
  const inLonRange = (n: number) => n >= -180 && n <= 180;

  const parseRow = (line: string): string[] => {
    const out: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') inQuotes = !inQuotes;
      else if ((c === "," || c === "\t") && !inQuotes) {
        out.push(cur.trim());
        cur = "";
      } else cur += c;
    }
    out.push(cur.trim());
    return out;
  };

  const firstRow = parseRow(lines[0]);
  const headerLower = firstRow.map((c) => c.toLowerCase().replace(/^\s+|\s+$/g, ""));
  let latIdx = -1;
  let lonIdx = -1;
  const latNames = ["lat", "latitude", "y"];
  const lonNames = ["lon", "lng", "longitude", "x"];
  for (let i = 0; i < headerLower.length; i++) {
    const h = headerLower[i];
    if (latNames.some((n) => h === n || h.startsWith(n + "_"))) latIdx = i;
    if (lonNames.some((n) => h === n || h.startsWith(n + "_"))) lonIdx = i;
  }
  const hasHeader = latIdx >= 0 && lonIdx >= 0;
  const startRow = hasHeader ? 1 : 0;
  if (!hasHeader) {
    latIdx = 0;
    lonIdx = 1;
  }

  const out: LocationPair[] = [];
  for (let r = startRow; r < lines.length; r++) {
    const cells = parseRow(lines[r]);
    const latVal = parseFloat(cells[latIdx] ?? "");
    const lonVal = parseFloat(cells[lonIdx] ?? "");
    if (Number.isNaN(latVal) || Number.isNaN(lonVal)) continue;
    let lat: number, lon: number;
    if (inLatRange(latVal) && inLonRange(lonVal)) {
      lat = latVal;
      lon = lonVal;
    } else if (inLonRange(latVal) && inLatRange(lonVal)) {
      lat = lonVal;
      lon = latVal;
    } else {
      lat = latVal;
      lon = lonVal;
    }
    if (inLatRange(lat) && inLonRange(lon)) out.push({ lat, lon });
  }
  return out;
}

/** Parse JSON: array of {lat,lon}, {latitude,longitude}, [lat,lon], or GeoJSON FeatureCollection. */
function parseLocationsFromJson(jsonText: string): LocationPair[] {
  const inLatRange = (n: number) => n >= -90 && n <= 90;
  const inLonRange = (n: number) => n >= -180 && n <= 180;
  const out: LocationPair[] = [];
  let data: unknown;
  try {
    data = JSON.parse(jsonText);
  } catch {
    return [];
  }
  if (Array.isArray(data)) {
    for (const item of data) {
      if (item == null) continue;
      let lat: number | undefined;
      let lon: number | undefined;
      if (typeof item === "object" && "lat" in item && "lon" in item) {
        lat = Number((item as { lat: unknown }).lat);
        lon = Number((item as { lon: unknown }).lon);
      } else if (typeof item === "object" && "latitude" in item && "longitude" in item) {
        lat = Number((item as { latitude: unknown }).latitude);
        lon = Number((item as { longitude: unknown }).longitude);
      } else if (Array.isArray(item) && item.length >= 2) {
        const a = Number(item[0]);
        const b = Number(item[1]);
        if (inLatRange(a) && inLonRange(b)) {
          lat = a;
          lon = b;
        } else if (inLonRange(a) && inLatRange(b)) {
          lat = b;
          lon = a;
        } else {
          lat = a;
          lon = b;
        }
      }
      if (lat != null && lon != null && !Number.isNaN(lat) && !Number.isNaN(lon) && inLatRange(lat) && inLonRange(lon)) {
        out.push({ lat, lon });
      }
    }
    return out;
  }
  if (typeof data === "object" && data != null && "features" in data) {
    const features = (data as { features: unknown[] }).features;
    if (!Array.isArray(features)) return [];
    for (const f of features) {
      if (f == null || typeof f !== "object" || !("geometry" in f)) continue;
      const geom = (f as { geometry: { type?: string; coordinates?: unknown[] } }).geometry;
      if (!geom || !Array.isArray(geom.coordinates)) continue;
      const coords = geom.coordinates;
      if (geom.type === "Point" && coords.length >= 2) {
        const lon = Number(coords[0]);
        const lat = Number(coords[1]);
        if (!Number.isNaN(lat) && !Number.isNaN(lon) && inLatRange(lat) && inLonRange(lon)) out.push({ lat, lon });
      }
    }
    return out;
  }
  return out;
}

function parseFileToLocations(file: File, text: string): LocationPair[] | { error: string } {
  const name = (file.name || "").toLowerCase();
  if (name.endsWith(".csv")) {
    const locs = parseLocationsFromCsv(text);
    return locs.length ? locs : { error: "No valid coordinates found in CSV." };
  }
  if (name.endsWith(".json") || name.endsWith(".geojson")) {
    const locs = parseLocationsFromJson(text);
    return locs.length ? locs : { error: "No valid coordinates found in JSON." };
  }
  if (text.trimStart().startsWith("[") || text.trimStart().startsWith("{")) {
    const locs = parseLocationsFromJson(text);
    return locs.length ? locs : { error: "No valid coordinates in JSON." };
  }
  const locs = parseLocationsFromCsv(text);
  return locs.length ? locs : { error: "No valid coordinates. Use .csv or .json file." };
}

export default function BatchView() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFile = useCallback((file: File, fileText: string) => {
    const result = parseFileToLocations(file, fileText);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setError(null);
    setText(locationsToText(result));
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const fileText = typeof reader.result === "string" ? reader.result : "";
        handleFile(file, fileText);
      };
      reader.readAsText(file, "UTF-8");
    },
    [handleFile]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false);
  }, []);

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const fileText = typeof reader.result === "string" ? reader.result : "";
        handleFile(file, fileText);
      };
      reader.readAsText(file, "UTF-8");
      e.target.value = "";
    },
    [handleFile]
  );

  return (
    <div className="batch-view">
      <div className="batch-input-section">
        <div className="section-label">Batch locations</div>
        <p className="batch-hint">
          Paste coordinates, or drag & drop a CSV/JSON file, or choose a file. One location per line in text; CSV/JSON can have headers. Max {BATCH_MAX} locations.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json,.geojson,text/csv,application/json"
          className="batch-file-input"
          aria-label="Choose CSV or JSON file"
          onChange={onFileInputChange}
        />
        <div
          className={`batch-dropzone ${dragOver ? "batch-dropzone-active" : ""}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <span className="batch-dropzone-text">Drag & drop CSV or JSON here</span>
          <button
            type="button"
            className="batch-choose-file-btn"
            onClick={() => fileInputRef.current?.click()}
          >
            or choose file
          </button>
        </div>
        <textarea
          className="batch-textarea"
          placeholder={"33.595 -7.632\n34.02,-6.83\n-7.65\t33.12\n# or drop a .csv / .json file above"}
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
