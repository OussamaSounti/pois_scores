# POI database export

Trimmed export of the POI PostgreSQL/PostGIS database for local development — a snapshot of the tables the upcoming POI cleaning & preprocessing pipeline produces.  
Schema reference: [DATA_MODEL.md](DATA_MODEL.md).

Source: PostgreSQL 16 + PostGIS 3.4, database `poi_db`, schemas `active` and `history`.

Dump files live in `data/` (gitignored — obtain separately):

| File | Purpose |
|------|---------|
| `data/poi_db_export.sql` | Full structure + data (~98 MB) — **load this** |
| `data/schema_only.sql` | Structure only (~25 KB) |

---

## Schemas

- **`active`** — current flat snapshot → `production_pois_current`
- **`history`** — SCD2 timeline → `production_poi_history`
- Taxonomy: `active.categories` (11 super-categories) + `active.category_mapping` (91 fclasses)

---

## Taxonomy (11 super-categories)

| Super-category | Example fclasses |
|----------------|------------------|
| Food & Drinks | restaurant, cafe, bar |
| Healthcare | pharmacy, hospital, clinic |
| Shopping | supermarket, mall, bakery |
| Education | school, university, library |
| Tourism & Accommodation | hotel, museum, cinema |
| Sport & Recreation | park, stadium, sports_centre |
| Finance | bank, atm |
| Transport | bus_stop, taxi, railway_station |
| Automotive & Traffic | fuel, parking, car_rental |
| Public Services & Government | post_office, police, town_hall |
| Religion | muslim, muslim_sunni |

> Religion fclasses exist in `active` only, not `history` (OSM tag derivation difference).

---

## Tables with data

| Table | ~Rows |
|-------|-------|
| `active.production_pois_current` | 72,600 |
| `history.production_poi_history` | 190,700 |
| `active.categories` | 11 |
| `active.category_mapping` | 91 |

Raw/staging tables (~27 GB) are structure-only in the export.

---

## Load into Docker Compose DB

```bash
docker compose up -d db
docker compose exec db psql -d poi_db -U poi_user -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker compose cp data/poi_db_export.sql db:/tmp/poi_db_export.sql
docker compose exec db psql -d poi_db -U poi_user -f /tmp/poi_db_export.sql
```

Verify:

```sql
SELECT super_category, count(*) FROM active.production_pois_current
GROUP BY super_category ORDER BY 2 DESC;
```

Full restore options: [GUIDE.md](GUIDE.md#restore-poi-dump-localdev).
