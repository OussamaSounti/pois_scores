/** Backend API base. In dev we use relative /api so Vite proxy forwards to backend. */
const API_BASE =
  typeof import.meta.env?.VITE_API_URL === "string" &&
  import.meta.env.VITE_API_URL.trim().length > 0
    ? import.meta.env.VITE_API_URL.replace(/\/$/, "")
    : import.meta.env.DEV
      ? ""
      : "http://localhost:8000";

export type ScoreResponse = {
  location: { lat: number; lon: number };
  scores: {
    poi_count_1km: number;
    poi_count_400m: number;
    n_categories: number;
    n_poi_types: number;
    entropy: number;
    entropy_fclass: number;
    by_category: Record<string, number>;
    accessibility_400m: Record<string, boolean>;
    nearest_km: Record<string, number>;
    aggregate_score: number | null;
  };
};

export type BatchResult = ScoreResponse[];
export const BATCH_MAX = 500;

export type PoiItem = {
  id: number;
  name: string;
  fclass: string;
  super_category: string;
  latitude: number;
  longitude: number;
  distance_km: number;
};

export async function fetchPois(
  lat: number,
  lon: number,
  radiusKm: number = 1
): Promise<PoiItem[]> {
  const res = await fetch(
    `${API_BASE}/api/v1/pois?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&radius_km=${encodeURIComponent(radiusKm)}`
  );
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
  const data = await res.json();
  return data.pois ?? [];
}

export async function fetchScore(lat: number, lon: number): Promise<ScoreResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/scores?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`
  );
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
  return res.json();
}

export async function fetchBatch(
  locations: Array<{ lat: number; lon: number }>
): Promise<BatchResult> {
  const res = await fetch(`${API_BASE}/api/v1/scores/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locations }),
  });
  if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
  const data = await res.json();
  return data.results ?? [];
}
