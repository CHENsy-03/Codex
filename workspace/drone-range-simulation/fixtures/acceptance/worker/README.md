# Canonical worker GeoTIFF acceptance fixture

`canonical_worker_map_v1.tif` is a permanent, deterministic, synthetic input for standalone-worker runtime acceptance. It contains no downloaded imagery, personal data, credentials, host paths, timestamps, or real mission data.

The fixture is a 32 x 32, single-band, uncompressed uint8 GeoTIFF in EPSG:4326. Its byte identity and fixed test vectors are recorded in `canonical_worker_map_v1.json`.

`generate_canonical_worker_map_v1.py` reconstructs the exact TIFF bytes using only the Python standard library and refuses to overwrite an existing file. Runtime acceptance must use the committed TIFF and verify its recorded SHA-256; it must not regenerate or modify the fixture during a product test.
