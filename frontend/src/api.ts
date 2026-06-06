/** Backend API base. In dev we use relative /api so Vite proxy forwards to backend. */
const API_BASE =
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
  id: number;
  name: string;
  fclass: string;
  super_category: string;
  latitude: number;
  longitude: number;
  distance_km: number;
};

type PropertyScores = {
  poi_refreshed_at: string | null;
  pipeline_version: string | null;
  poi_count_1km: number | null;
  poi_count_400m: number | null;
  n_categories: number | null;
  n_poi_types: number | null;
  entropy: number | null;
  entropy_fclass: number | null;
  entropy_norm: number | null;
  entropy_fclass_norm: number | null;
  aggregate_score: number | null;
  accessibility_400m: Record<string, boolean>;
  by_category: Record<string, number>;
  nearest_km: Record<string, number>;
  dist_coast_km: number | null;
  land_buffer_fraction_1km: number | null;
  transaction_date: string | null;
  poi_source: string | null;
};

export type PropertyMapItem = {
  id: number;
  latitude: number;
  longitude: number;
  transaction_date: string | null;
  asset_price: number | null;
  asset_surface: number | null;
  asset_psqm: number | null;
  asset_type: string | null;
  district_uid: string | null;
  district_name: string | null;
  neighbourhood_uid: string | null;
  neighbour_name: string | null;
  iris_uid: string | null;
  iris_code: string | null;
  ilot_uid: string | null;
  ilot_objectid: string | null;
  scores: PropertyScores;
};

export type PropertyStatsGroup = {
  key: string;
  label: string;
  properties_count: number;
  avg_poi_count_1km: number | null;
  avg_entropy: number | null;
  avg_entropy_fclass: number | null;
  avg_aggregate_score: number | null;
};

export type PropertyLevel = 'district' | 'neighbourhood' | 'iris' | 'ilot';

export type PropertiesFilters = {
  district_uid?: string;
  neighbourhood_uid?: string;
  iris_uid?: string;
  ilot_uid?: string;
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
  return data.pois ?? [];
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

export async function fetchPropertiesMap(
  bbox: { west: number; south: number; east: number; north: number },
  filters: PropertiesFilters = {},
  limit: number = 1200
): Promise<{ items: PropertyMapItem[]; count: number }> {
  const params = new URLSearchParams({
    west: String(bbox.west),
    south: String(bbox.south),
    east: String(bbox.east),
    north: String(bbox.north),
    limit: String(limit),
  });
  if (filters.district_uid) params.set('district_uid', filters.district_uid);
  if (filters.neighbourhood_uid) params.set('neighbourhood_uid', filters.neighbourhood_uid);
  if (filters.iris_uid) params.set('iris_uid', filters.iris_uid);
  if (filters.ilot_uid) params.set('ilot_uid', filters.ilot_uid);

  const res = await fetch(`${API_BASE}/api/v1/properties?${params.toString()}`);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  const data = await res.json();
  return { items: data.items ?? [], count: data.count ?? 0 };
}

export async function fetchPropertyDetail(propertyId: number): Promise<PropertyMapItem> {
  const res = await fetch(`${API_BASE}/api/v1/properties/${propertyId}`);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  const data = await res.json();
  return data.item;
}

export async function fetchPropertyStats(
  level: PropertyLevel,
  filters: PropertiesFilters = {}
): Promise<PropertyStatsGroup[]> {
  const params = new URLSearchParams({ level });
  if (filters.district_uid) params.set('district_uid', filters.district_uid);
  if (filters.neighbourhood_uid) params.set('neighbourhood_uid', filters.neighbourhood_uid);
  if (filters.iris_uid) params.set('iris_uid', filters.iris_uid);
  if (filters.ilot_uid) params.set('ilot_uid', filters.ilot_uid);

  const res = await fetch(`${API_BASE}/api/v1/properties/stats?${params.toString()}`);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  const data = await res.json();
  return data.groups ?? [];
}
