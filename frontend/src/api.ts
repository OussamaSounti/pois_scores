/** Backend API base. In dev we use relative /api so Vite proxy forwards to backend. */
export const API_BASE =
  typeof import.meta.env?.VITE_API_URL === 'string' &&
  import.meta.env.VITE_API_URL.trim().length > 0
    ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
    : import.meta.env.DEV
      ? ''
      : 'http://localhost:8000';

export type ScoreResponse = {
  location: { lat: number; lon: number };
  scores: {
    poi_count_1km: number;
    poi_count_400m: number;
    n_categories: number;
    n_poi_types: number;
    entropy: number;
    entropy_fclass: number;
    entropy_norm: number;
    entropy_fclass_norm: number;
    by_category: Record<string, number>;
    accessibility_400m: Record<string, boolean>;
    nearest_km: Record<string, number>;
    aggregate_score: number | null;
    dist_coast_km: number | null;
    land_buffer_fraction_1km: number | null;
    poi_source: string | null;
  };
};

export type BatchResult = ScoreResponse[];
export const BATCH_MAX = 500;

export type PoiItem = {
  id: string;
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
  radiusKm: number = 1,
  asOf?: string
): Promise<PoiItem[]> {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
  });
  if (asOf) params.set('as_of', asOf);
  const res = await fetch(`${API_BASE}/api/v1/pois?${params.toString()}`);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  const data = await res.json();
  const pois = data.pois ?? [];
  // Accept both the current wire contract (osm_id/lat/lon) and the older
  // one (id/latitude/longitude) so a stale backend cannot blank the map.
  return pois.map((p: any) => ({
    ...p,
    id: String(p.osm_id ?? p.id),
    latitude: p.lat ?? p.latitude,
    longitude: p.lon ?? p.longitude,
  }));
}

export async function fetchScore(
  lat: number,
  lon: number,
  asOf?: string
): Promise<ScoreResponse> {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
  });
  if (asOf) params.set('as_of', asOf);
  const res = await fetch(`${API_BASE}/api/v1/scores?${params.toString()}`);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return res.json();
}

export async function fetchBatch(
  locations: Array<{ lat: number; lon: number; as_of?: string }>
): Promise<BatchResult> {
  const res = await fetch(`${API_BASE}/api/v1/scores/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ locations }),
  });
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  const data = await res.json();
  return data.results ?? [];
}

