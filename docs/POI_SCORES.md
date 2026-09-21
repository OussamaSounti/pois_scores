# POI Scores Calculation

This document outlines all the Points of Interest (POI) scores calculated by the system and details the exact mathematical logic used to derive them.

## Base Metrics

Before calculating the aggregate score, the system computes several fundamental metrics within two radii (1km and 400m) around the target location:

- **`poi_count_1km`**: Total number of POIs within 1 kilometer.
- **`poi_count_400m`**: Total number of POIs within 400 meters.
- **`n_categories`**: Total number of unique POI *super categories* present within 1km.
- **`n_poi_types`**: Total number of unique POI *functional classes* (`fclass`) present within 1km.
- **`accessibility_400m`**: A boolean dictionary indicating the presence of specific essential POI functional classes within a 400m walking distance. The specific tracked types are: `bus_stop`, `pharmacy`, `school`, `hospital`, `supermarket`, `bank`, `atm`, `clinic`, `fuel`, `police`, `park`, `doctors`, and `taxi`.
- **`land_buffer_fraction_1km`**: The fraction of the 1km buffer that is over land (e.g., `1.0` for inland properties, `< 1.0` for coastal properties). This ensures coastal properties aren't penalized for having half of their buffer in the sea.

## Diversity and Distribution Metrics (Entropy)

To measure the evenness and variety of the POI distribution, the system calculates Shannon Entropy metrics:

- **`entropy`**: Shannon entropy of the POI distribution by super category within 1km.
- **`entropy_norm`**: Normalized entropy, bounded between 0 and 1, calculated as `min(1.0, entropy / log2(N_SUPER_CATEGORIES))`.
- **`entropy_fclass`**: Shannon entropy of the POI distribution by functional class (`fclass`) within 1km.
- **`entropy_fclass_norm`**: Normalized fclass entropy, bounded between 0 and 1, calculated as `min(1.0, entropy_fclass / log2(N_FCLASS_TYPES))`.

## Aggregate Score Calculation

The final `aggregate_score` is a weighted composite metric (out of 100) based on three main pillars: **Density**, **Diversity**, and **Accessibility**.

### 1. Density Score (30% weight)
Calculates how densely populated the area is with POIs, normalizing for coastal geography.
```python
effective_count_1km = total_1km / land_buffer_fraction_1km
density_score = min(effective_count_1km / 50.0, 1.0)
```
*(Caps at 1.0 when there are at least 50 effective POIs within 1km).*

### 2. Diversity Score (30% weight)
Measures the variety of amenities available, using both high-level categories and specific functional classes.
```python
diversity_score = min((n_categories / 10.0 + n_poi_types / 20.0) / 2, 1.0)
```
*(Caps at 1.0 when the area has a rich mix of categories and types).*

### 3. Accessibility Score (40% weight)
Evaluates the immediate walkability (400m) to key essential amenities.
```python
accessibility_score = sum(accessibility_400m) / len(ACCESSIBILITY_KEY_TYPES)
```
*(Percentage of key amenity types available within 400 meters).*

### Final Formula
The overall score is a weighted sum mapped to a 0-100 scale:
```python
aggregate_score = round(100.0 * (0.3 * density_score + 0.3 * diversity_score + 0.4 * accessibility_score), 1)
```

## Additional Proximity Metrics
The payload also returns the following distance metrics:
- **`nearest_km`**: The minimum distance in kilometers to the nearest POI for each of the 11 high-level **super categories** (e.g., commercial, education, health). The system searches up to a maximum radius of 25 kilometers to find these nearest matches.
- **`dist_coast_km`**: The precise distance to the coastline in kilometers.
