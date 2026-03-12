# Batch input samples

Use these files to test the **Batch** tab: drag and drop them onto the drop zone or choose them via “or choose file”. All coordinates are in Morocco.

| File | Description |
|------|-------------|
| `batch_lat_lon.csv` | CSV with `lat`, `lon`, `site_id`, `name`. Tests header detection and row labels from `site_id`/`name`. |
| `batch_latitude_longitude.csv` | CSV with `latitude`, `longitude`, `location_id`, `notes`. Tests alternate column names. |
| `batch_extra_columns.csv` | CSV with `id`, `city`, `region`, `y` (lat), `x` (lon). Tests auto-detection when lat/lon columns have generic names among other variables. |
| `batch_no_header.csv` | Plain CSV with no header; first two columns are lat, lon. Tests headerless parsing. |
| `batch_locations.json` | JSON array of objects with `lat`/`lon` or `latitude`/`longitude` and `id`/`name`. Tests JSON parsing and row labels. |
| `batch_points.geojson` | GeoJSON FeatureCollection of Points. Tests GeoJSON and labels from `id` or `properties.name`. |

After loading a file, click **Run batch** to compute scores. The **Input row** column in the results will show the row label from the file (e.g. site_id, name, or “Row 1”, “Row 2”). Use **Export CSV** to download results including the `input_row` column when labels were loaded.
