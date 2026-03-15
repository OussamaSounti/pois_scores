import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPois, fetchScore, type PoiItem, type ScoreResponse } from './api';

describe('api', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetchScore calls correct URL and returns ScoreResponse shape', async () => {
    const mockJson: ScoreResponse = {
      location: { lat: 33.5, lon: -7.6 },
      scores: {
        poi_count_1km: 10,
        poi_count_400m: 2,
        n_categories: 3,
        n_poi_types: 5,
        entropy: 1.5,
        entropy_fclass: 2.0,
        by_category: {},
        accessibility_400m: {},
        nearest_km: {},
        aggregate_score: 42,
      },
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockJson),
    });

    const result = await fetchScore(33.5, -7.6);

    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/scores?lat=33.5&lon=-7.6'));
    expect(result).toEqual(mockJson);
    expect(result.location.lat).toBe(33.5);
    expect(result.scores.poi_count_1km).toBe(10);
  });

  it('fetchPois returns empty array when response has no pois key', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    const result = await fetchPois(33.5, -7.6, 1);

    expect(result).toEqual([]);
  });

  it('fetchPois returns PoiItem[] when response has pois', async () => {
    const mockPois: PoiItem[] = [
      {
        id: 1,
        name: 'Test',
        fclass: 'pharmacy',
        super_category: 'Healthcare',
        latitude: 33.5,
        longitude: -7.6,
        distance_km: 0.5,
      },
    ];
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ pois: mockPois }),
    });

    const result = await fetchPois(33.5, -7.6, 2);

    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/pois\?.*radius_km=2/));
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Test');
    expect(result[0].distance_km).toBe(0.5);
  });
});
