"""Integration tests for score API (single and batch).

Require Postgres with active.production_pois_current.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _ready() -> bool:
    """Return True if /ready returns 200."""
    r = client.get("/ready")
    return r.status_code == 200


@pytest.mark.skipif(not _ready(), reason="Database not available (start Postgres and restore dump)")
class TestHealth:
    def test_health_ok(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_ready_ok(self) -> None:
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.skipif(not _ready(), reason="Database not available")
class TestSingleScore:
    def test_get_scores_query_params(self) -> None:
        r = client.get("/api/v1/scores", params={"lat": 33.5, "lon": -7.6})
        assert r.status_code == 200
        data = r.json()
        assert "location" in data
        assert data["location"]["lat"] == 33.5
        assert data["location"]["lon"] == -7.6
        assert "scores" in data
        s = data["scores"]
        assert "poi_count_1km" in s
        assert "poi_count_400m" in s
        assert "n_categories" in s
        assert "n_poi_types" in s
        assert "entropy" in s
        assert "entropy_fclass" in s
        assert "by_category" in s
        assert "accessibility_400m" in s
        assert "nearest_km" in s

    def test_post_scores_body(self) -> None:
        r = client.post("/api/v1/scores", json={"lat": 33.5, "lon": -7.6})
        assert r.status_code == 200
        data = r.json()
        assert data["location"]["lat"] == 33.5
        assert data["location"]["lon"] == -7.6
        assert "scores" in data

    def test_invalid_coords_422(self) -> None:
        r = client.get("/api/v1/scores", params={"lat": 99, "lon": -7.6})
        assert r.status_code == 422

    def test_get_scores_computation_error_500(self) -> None:
        with patch("app.features.scores.router.compute_scores") as mock_compute:
            mock_compute.side_effect = RuntimeError("db unavailable")
            r = client.get("/api/v1/scores", params={"lat": 33.5, "lon": -7.6})
        assert r.status_code == 500
        assert "Score computation failed" in r.json()["detail"]
        assert "db unavailable" in r.json()["detail"]

    def test_post_scores_computation_error_500(self) -> None:
        with patch("app.features.scores.router.compute_scores") as mock_compute:
            mock_compute.side_effect = ValueError("invalid geom")
            r = client.post("/api/v1/scores", json={"lat": 33.5, "lon": -7.6})
        assert r.status_code == 500
        assert "Score computation failed" in r.json()["detail"]
        assert "invalid geom" in r.json()["detail"]


@pytest.mark.skipif(not _ready(), reason="Database not available")
class TestPoisList:
    def test_pois_list_ok(self) -> None:
        r = client.get("/api/v1/pois", params={"lat": 33.5, "lon": -7.6})
        assert r.status_code == 200
        data = r.json()
        assert "pois" in data
        assert isinstance(data["pois"], list)
        for p in data["pois"][:3]:
            assert "osm_id" in p and "name" in p and "fclass" in p
            assert "super_category" in p and "lat" in p and "lon" in p
            assert "distance_km" in p

    def test_pois_radius_param(self) -> None:
        r = client.get("/api/v1/pois", params={"lat": 33.5, "lon": -7.6, "radius_km": 0.5})
        assert r.status_code == 200
        assert "pois" in r.json()


@pytest.mark.skipif(not _ready(), reason="Database not available")
class TestBatchScores:
    def test_batch_two_locations(self) -> None:
        r = client.post(
            "/api/v1/scores/batch",
            json={
                "locations": [
                    {"lat": 33.5, "lon": -7.6},
                    {"lat": 34.0, "lon": -6.8},
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["location"]["lat"] == 33.5
        assert data["results"][0]["location"]["lon"] == -7.6
        assert data["results"][1]["location"]["lat"] == 34.0
        assert data["results"][1]["location"]["lon"] == -6.8
        assert "scores" in data["results"][0]
        assert "entropy_fclass" in data["results"][0]["scores"]

    def test_batch_order_preserved(self) -> None:
        locations = [{"lat": 33.0 + i * 0.1, "lon": -7.0 - i * 0.1} for i in range(3)]
        r = client.post("/api/v1/scores/batch", json={"locations": locations})
        assert r.status_code == 200
        results = r.json()["results"]
        for i, loc in enumerate(locations):
            assert results[i]["location"]["lat"] == loc["lat"]
            assert results[i]["location"]["lon"] == loc["lon"]

    def test_batch_over_limit_422(self) -> None:
        # Max 500; send 501
        locations = [{"lat": 33.5, "lon": -7.6}] * 501
        r = client.post("/api/v1/scores/batch", json={"locations": locations})
        assert r.status_code == 422

    def test_batch_empty_422(self) -> None:
        r = client.post("/api/v1/scores/batch", json={"locations": []})
        assert r.status_code == 422

    def test_batch_computation_error_500(self) -> None:
        with patch("app.features.scores.router.compute_scores") as mock_compute:
            mock_compute.side_effect = Exception("connection lost")
            r = client.post(
                "/api/v1/scores/batch",
                json={"locations": [{"lat": 33.5, "lon": -7.6}]},
            )
        assert r.status_code == 500
        assert "Score computation failed" in r.json()["detail"]
        assert "connection lost" in r.json()["detail"]
