import { useCallback, useMemo, useRef, useState } from "react";
import { fetchBatch, BATCH_MAX, type BatchResult, type ScoreResponse } from "../api";

/** Build CSV string with full POI scores for each location (one row per location). Optionally prepend input_row from rowMeta. */
function buildScoresCsv(results: BatchResult, rowMeta?: RowMeta[]): string {
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

  const hasInputRow = rowMeta != null && rowMeta.length === results.length;
  const header =
    [
      ...(hasInputRow ? ["input_row"] : []),
      "lat",
      "lon",
      ...scalarKeys.filter((k) => k !== "lat" && k !== "lon"),
      ...catKeys.map((k) => `category_${k}`),
      ...accKeys.map((k) => `acc_${k}`),
      ...nearestKeys.map((k) => `nearest_km_${k}`),
    ].join(",");

  const rows = results.map((r: ScoreResponse, i: number) => {
    const s = r.scores;
    const inputRowCell = hasInputRow && rowMeta![i] ? escape(rowMeta![i].label) : "";
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
    const rest = [...scalars, ...catVals, ...accVals, ...nearestVals].map(escape).join(",");
    return hasInputRow ? `${inputRowCell},${rest}` : rest;
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

export type RowMeta = { id?: string; label: string };

function locationsToText(locations: LocationPair[]): string {
  return locations.map(({ lat, lon }) => `${lat} ${lon}`).join("\n");
}

const inLatRange = (n: number) => n >= -90 && n <= 90;
const inLonRange = (n: number) => n >= -180 && n <= 180;

function parseCsvRow(line: string): string[] {
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
}

/** Parse CSV with auto-detection of lat/lon columns by value ranges; returns locations and row labels for linking. */
function parseLocationsFromCsv(csvText: string): { locations: LocationPair[]; rowMeta: RowMeta[] } {
  const lines = csvText.trim().split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const locations: LocationPair[] = [];
  const rowMeta: RowMeta[] = [];
  if (lines.length === 0) return { locations, rowMeta };

  const rows = lines.map(parseCsvRow);
  const nCols = Math.max(0, ...rows.map((r) => r.length));
  if (nCols < 2) return { locations, rowMeta };

  const latNames = ["lat", "latitude", "y"];
  const lonNames = ["lon", "lng", "longitude", "x"];

  function looksLikeHeader(cells: string[]): boolean {
    return cells.every((c) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(c.trim()) || c.trim() === "");
  }

  let startRow = 0;
  const headerRow = rows[0];
  const hasHeader = headerRow && looksLikeHeader(headerRow);
  if (hasHeader && rows.length > 1) startRow = 1;

  const dataRows = rows.slice(startRow);
  const numRows = dataRows.length;
  if (numRows === 0) return { locations, rowMeta };

  const headerLower = (hasHeader ? headerRow : []).map((c) => c.toLowerCase().trim());

  function columnNumericValues(colIdx: number): number[] {
    const vals: number[] = [];
    for (const row of dataRows) {
      const v = parseFloat((row[colIdx] ?? "").trim());
      if (!Number.isNaN(v)) vals.push(v);
    }
    return vals;
  }

  function scoreLat(colIdx: number): number {
    const vals = columnNumericValues(colIdx);
    if (vals.length === 0) return 0;
    const inRange = vals.filter(inLatRange).length;
    return inRange / vals.length;
  }
  function scoreLon(colIdx: number): number {
    const vals = columnNumericValues(colIdx);
    if (vals.length === 0) return 0;
    const inRange = vals.filter(inLonRange).length;
    return inRange / vals.length;
  }

  let latIdx = -1;
  let lonIdx = -1;
  for (let i = 0; i < nCols; i++) {
    const h = headerLower[i] ?? "";
    const isLatName = latNames.some((n) => h === n || h.startsWith(n + "_"));
    const isLonName = lonNames.some((n) => h === n || h.startsWith(n + "_"));
    const slat = scoreLat(i);
    const slon = scoreLon(i);
    if (isLatName && latIdx < 0) latIdx = i;
    else if (isLonName && lonIdx < 0) lonIdx = i;
    if (latIdx < 0 && slat >= 0.8 && (lonIdx < 0 || i !== lonIdx)) {
      if (latIdx < 0 || slat > scoreLat(latIdx)) latIdx = i;
    }
    if (lonIdx < 0 && slon >= 0.8 && (latIdx < 0 || i !== latIdx)) {
      if (lonIdx < 0 || slon > scoreLon(lonIdx)) lonIdx = i;
    }
  }
  if (latIdx < 0 || lonIdx < 0) {
    const numericCols: number[] = [];
    for (let i = 0; i < nCols; i++) {
      const vals = columnNumericValues(i);
      if (vals.length >= numRows * 0.5) numericCols.push(i);
    }
    if (latIdx < 0 && numericCols[0] != null) latIdx = numericCols[0];
    if (lonIdx < 0 && numericCols[1] != null) lonIdx = numericCols[1];
    if (latIdx === lonIdx && numericCols.length > 1) lonIdx = numericCols[1];
  }
  if (latIdx < 0) latIdx = 0;
  if (lonIdx < 0) lonIdx = 1;
  if (latIdx === lonIdx) lonIdx = latIdx === 0 ? 1 : 0;

  let labelCol = -1;
  for (let i = 0; i < nCols; i++) {
    if (i !== latIdx && i !== lonIdx) {
      const h = (headerLower[i] ?? "").toLowerCase();
      if (h === "id" || h === "name" || h === "label" || h.startsWith("id_") || h === "site") {
        labelCol = i;
        break;
      }
    }
  }
  if (labelCol < 0) {
    for (let i = 0; i < nCols; i++) if (i !== latIdx && i !== lonIdx) { labelCol = i; break; }
  }

  for (let r = 0; r < dataRows.length; r++) {
    const cells = dataRows[r];
    const latVal = parseFloat((cells[latIdx] ?? "").trim());
    const lonVal = parseFloat((cells[lonIdx] ?? "").trim());
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
    if (!inLatRange(lat) || !inLonRange(lon)) continue;
    locations.push({ lat, lon });
    const label = labelCol >= 0 ? (cells[labelCol] ?? "").trim() : "";
    rowMeta.push({ id: label || undefined, label: label || `Row ${locations.length}` });
  }
  return { locations, rowMeta };
}

/** Parse JSON; returns locations and rowMeta for linking results to input. */
function parseLocationsFromJson(jsonText: string): { locations: LocationPair[]; rowMeta: RowMeta[] } {
  const locations: LocationPair[] = [];
  const rowMeta: RowMeta[] = [];
  let data: unknown;
  try {
    data = JSON.parse(jsonText);
  } catch {
    return { locations, rowMeta };
  }
  function labelFor(outputIndex: number, obj: Record<string, unknown> | null): string {
    if (obj && typeof obj.id !== "undefined") return String(obj.id);
    if (obj && typeof obj.name === "string") return obj.name;
    if (obj && typeof obj === "object" && obj !== null && "properties" in obj) {
      const p = (obj as { properties?: Record<string, unknown> }).properties;
      if (p && typeof p === "object") {
        if (typeof p.id !== "undefined") return String(p.id);
        if (typeof p.name === "string") return p.name;
      }
    }
    return `Row ${outputIndex + 1}`;
  }
  if (Array.isArray(data)) {
    for (const item of data) {
      if (item == null) continue;
      let lat: number | undefined;
      let lon: number | undefined;
      const obj = typeof item === "object" && item !== null ? (item as Record<string, unknown>) : null;
      if (obj && "lat" in item && "lon" in item) {
        lat = Number((item as { lat: unknown }).lat);
        lon = Number((item as { lon: unknown }).lon);
      } else if (obj && "latitude" in item && "longitude" in item) {
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
        locations.push({ lat, lon });
        rowMeta.push({ label: labelFor(locations.length - 1, obj) });
      }
    }
    return { locations, rowMeta };
  }
  if (typeof data === "object" && data != null && "features" in data) {
    const features = (data as { features: unknown[] }).features;
    if (!Array.isArray(features)) return { locations, rowMeta };
    features.forEach((f, i) => {
      if (f == null || typeof f !== "object" || !("geometry" in f)) return;
      const geom = (f as { geometry: { type?: string; coordinates?: unknown[] }; id?: unknown; properties?: Record<string, unknown> }).geometry;
      const feat = f as { id?: unknown; properties?: Record<string, unknown> };
      if (!geom || !Array.isArray(geom.coordinates)) return;
      const coords = geom.coordinates;
      if (geom.type === "Point" && coords.length >= 2) {
        const lon = Number(coords[0]);
        const lat = Number(coords[1]);
        if (!Number.isNaN(lat) && !Number.isNaN(lon) && inLatRange(lat) && inLonRange(lon)) {
          locations.push({ lat, lon });
          rowMeta.push({ label: labelFor(i, feat) });
        }
      }
    });
  }
  return { locations, rowMeta };
}

type FileParseResult = { locations: LocationPair[]; rowMeta: RowMeta[] } | { error: string };

function parseFileToLocations(file: File, text: string): FileParseResult {
  const name = (file.name || "").toLowerCase();
  if (name.endsWith(".csv")) {
    const out = parseLocationsFromCsv(text);
    return out.locations.length ? out : { error: "No valid coordinates found in CSV." };
  }
  if (name.endsWith(".json") || name.endsWith(".geojson")) {
    const out = parseLocationsFromJson(text);
    return out.locations.length ? out : { error: "No valid coordinates found in JSON." };
  }
  if (text.trimStart().startsWith("[") || text.trimStart().startsWith("{")) {
    const out = parseLocationsFromJson(text);
    return out.locations.length ? out : { error: "No valid coordinates in JSON." };
  }
  const out = parseLocationsFromCsv(text);
  return out.locations.length ? out : { error: "No valid coordinates. Use .csv or .json file." };
}

export default function BatchView() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<BatchResult | null>(null);
  const [rowMeta, setRowMeta] = useState<RowMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showBatchHelp, setShowBatchHelp] = useState(false);
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
    const csv = buildScoresCsv(results, rowMeta.length === results.length ? rowMeta : undefined);
    const filename = `batch_scores_${new Date().toISOString().slice(0, 10)}.csv`;
    downloadCsv(csv, filename);
  }, [results, rowMeta]);

  const canExport = useMemo(() => results != null && results.length > 0, [results]);

  const handleFile = useCallback((file: File, fileText: string) => {
    const result = parseFileToLocations(file, fileText);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setError(null);
    setText(locationsToText(result.locations));
    setRowMeta(result.rowMeta);
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
        <div className="batch-section-header">
          <span className="section-label">Batch locations</span>
          <button
            type="button"
            className="batch-help-toggle"
            onClick={() => setShowBatchHelp((v) => !v)}
            aria-expanded={showBatchHelp}
          >
            {showBatchHelp ? "Hide help" : "How does batch input work?"}
          </button>
        </div>
        <p className="batch-hint">
          Paste coordinates or drag & drop CSV/JSON. Lat/lon columns are auto-detected; extra columns link results to your input rows. Max {BATCH_MAX} locations.
        </p>
        {showBatchHelp && (
          <div className="batch-help" role="region" aria-label="Batch input help">
            <h4 className="batch-help-title">Ways to provide locations</h4>
            <ul className="batch-help-list">
              <li><strong>Paste</strong> — Type or paste coordinates in the text area below (one location per line).</li>
              <li><strong>Drag & drop</strong> — Drop a CSV or JSON file onto the drop zone; it will be parsed and the text area filled with the detected coordinates.</li>
              <li><strong>Choose file</strong> — Click “or choose file” to pick a .csv or .json file from your computer.</li>
            </ul>

            <h4 className="batch-help-title">Plain text (paste)</h4>
            <p>One location per line. The first two numbers on each line are used as coordinates.</p>
            <ul className="batch-help-list">
              <li><strong>Order</strong> — Lat/lon or lon/lat is auto-detected from value ranges (latitude −90 to 90, longitude −180 to 180).</li>
              <li><strong>Separators</strong> — Space, comma, tab, semicolon, or pipe between the two numbers.</li>
              <li><strong>Comments</strong> — Lines starting with <code>#</code> or <code>//</code> are ignored.</li>
              <li><strong>Header</strong> — If the first line looks like column names (e.g. <code>lat,lon</code>), it is skipped.</li>
              <li>Extra numbers or text on the line are ignored; only the first two valid coordinates are used.</li>
            </ul>

            <h4 className="batch-help-title">CSV files</h4>
            <p>Latitude and longitude columns are detected automatically so you can use files with many other columns.</p>
            <ul className="batch-help-list">
              <li><strong>Auto-detection</strong> — Columns whose values mostly fall in −90…90 (latitude) or −180…180 (longitude) are chosen. Header names like <code>lat</code>, <code>latitude</code>, <code>lon</code>, <code>longitude</code>, <code>x</code>, <code>y</code> are also used when present.</li>
              <li><strong>Header row</strong> — If the first row looks like headers (letters/underscores only), it is skipped.</li>
              <li><strong>Row labels</strong> — To link each result back to your file, the first column that is not lat/lon is used as the row label (e.g. site ID, name). Columns named <code>id</code>, <code>name</code>, <code>label</code>, or <code>site</code> are preferred. These labels appear in the “Input row” column of the results and in the exported CSV.</li>
            </ul>

            <h4 className="batch-help-title">JSON files</h4>
            <p>Arrays of coordinates or GeoJSON are supported.</p>
            <ul className="batch-help-list">
              <li><strong>Array of objects</strong> — <code>{`[{ "lat": 33.5, "lon": -7.6 }, ...]`}</code> or <code>{`[{ "latitude", "longitude" }, ...]`}</code>. If objects have <code>id</code> or <code>name</code>, that value is used as the input row label.</li>
              <li><strong>Array of arrays</strong> — <code>{`[[33.5, -7.6], ...]`}</code> (lat/lon or lon/lat is inferred).</li>
              <li><strong>GeoJSON</strong> — <code>{`{ "type": "FeatureCollection", "features": [...] }`}</code> with Point geometries. <code>feature.id</code> or <code>properties.id</code> / <code>properties.name</code> are used as the row label when present.</li>
            </ul>

            <h4 className="batch-help-title">Results and export</h4>
            <ul className="batch-help-list">
              <li>The <strong>Input row</strong> column in the results table shows the label from your file (or “Row 1”, “Row 2”, … if no label was found), so you can match each score to the correct line in your input.</li>
              <li><strong>Export CSV</strong> includes all score fields. If you loaded from a file with row labels, the exported CSV also has an <code>input_row</code> column so you can join results back to your original data.</li>
            </ul>

            <p className="batch-help-limit">Maximum {BATCH_MAX} locations per batch.</p>
          </div>
        )}
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
          onChange={(e) => {
            setText(e.target.value);
            setRowMeta([]);
          }}
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
                <th>Input row</th>
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
                  <td className="batch-input-row-cell">
                    {rowMeta.length === results.length && rowMeta[i] ? rowMeta[i].label : `Row ${i + 1}`}
                  </td>
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
