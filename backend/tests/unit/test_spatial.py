"""Unit tests for spatial service (entropy, haversine)."""

import math

from app.services.spatial import _entropy, _haversine_km, _land_buffer_fraction


class TestHaversine:
    """Tests for _haversine_km."""

    def test_same_point_zero_distance(self) -> None:
        assert _haversine_km(33.5, -7.6, 33.5, -7.6) == 0.0

    def test_antipodal_roughly_half_earth_circumference(self) -> None:
        # Earth circumference ~40075 km; half ~20037 km
        d = _haversine_km(0.0, 0.0, 0.0, 180.0)
        assert 19900 < d < 20100

    def test_known_distance_casablanca_rabat(self) -> None:
        # Casablanca ~33.57, -7.59; Rabat ~34.02, -6.83; ~90 km
        d = _haversine_km(33.57, -7.59, 34.02, -6.83)
        assert 85 < d < 95

    def test_symmetry(self) -> None:
        a = _haversine_km(33.5, -7.6, 34.0, -6.5)
        b = _haversine_km(34.0, -6.5, 33.5, -7.6)
        assert a == b


class TestEntropy:
    """Tests for _entropy."""

    def test_zero_total_returns_zero(self) -> None:
        assert _entropy({"a": 0}, 0) == 0.0
        assert _entropy({}, 0) == 0.0

    def test_single_category_zero_entropy(self) -> None:
        assert _entropy({"Transport": 10}, 10) == 0.0

    def test_two_equal_categories(self) -> None:
        # 50-50 split: entropy = 1 bit
        h = _entropy({"A": 5, "B": 5}, 10)
        assert abs(h - 1.0) < 1e-6

    def test_uniform_four_categories(self) -> None:
        # 4 categories, 25% each: entropy = 2 bits
        h = _entropy({"A": 25, "B": 25, "C": 25, "D": 25}, 100)
        assert abs(h - 2.0) < 1e-5

    def test_skewed_distribution(self) -> None:
        # One dominant category -> lower entropy
        h_skewed = _entropy({"A": 90, "B": 10}, 100)
        h_uniform = _entropy({"A": 50, "B": 50}, 100)
        assert h_skewed < h_uniform
        assert h_skewed > 0


class TestLandBufferFraction:
    """Tests for _land_buffer_fraction (circular-segment formula)."""

    def test_far_from_coast_returns_one(self) -> None:
        # Distance >= radius → entirely on land
        assert _land_buffer_fraction(2.0, radius_km=1.0) == 1.0
        assert _land_buffer_fraction(1.0, radius_km=1.0) == 1.0

    def test_on_coast_returns_half(self) -> None:
        # Right on the coastline → exactly half the buffer is on land
        result = _land_buffer_fraction(0.0, radius_km=1.0)
        assert abs(result - 0.5) < 1e-6

    def test_near_coast_between_half_and_one(self) -> None:
        # 500 m from a 1 km buffer coast → land fraction between 0.5 and 1.0
        result = _land_buffer_fraction(0.5, radius_km=1.0)
        assert 0.5 < result < 1.0

    def test_fraction_increases_with_distance(self) -> None:
        fracs = [_land_buffer_fraction(d, radius_km=1.0) for d in [0.0, 0.25, 0.5, 0.75, 1.0]]
        assert fracs == sorted(fracs)

    def test_formula_value_at_half_radius(self) -> None:
        # d = r/2 → ratio = 0.5
        # ocean_fraction = (arccos(0.5) - 0.5*sqrt(0.75)) / pi
        ratio = 0.5
        expected_ocean = (math.acos(ratio) - ratio * math.sqrt(1 - ratio**2)) / math.pi
        expected = 1.0 - expected_ocean
        result = _land_buffer_fraction(0.5, radius_km=1.0)
        assert abs(result - expected) < 1e-9

    def test_clamps_to_valid_range(self) -> None:
        # No result should be outside [0, 1]
        for d in [-1.0, 0.0, 0.3, 1.0, 5.0]:
            r = _land_buffer_fraction(d, radius_km=1.0)
            assert 0.0 <= r <= 1.0
