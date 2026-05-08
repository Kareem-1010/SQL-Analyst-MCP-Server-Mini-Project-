# Fixtures — Synthetic Dataset

This directory contains fixed-seed synthetic datasets used in the QueryMind AI research evaluation.

## Files

| File | Description | Rows |
|------|-------------|------|
| `sample_upload.csv` | Multi-column sales/product dataset for upload testing | ~50 |

## Reproducibility

All datasets are generated with a fixed random seed (`SEED=42`) to ensure reproducible benchmark runs.

To regenerate:
```bash
cd backend
python scripts/seed_demo_data.py --seed 42 --out scripts/fixtures/
```

## Schema

`sample_upload.csv` contains the following columns:
- `product_id` — Unique integer identifier
- `product_name` — String product name
- `category` — Product category label
- `unit_price` — Decimal price (USD)
- `units_sold` — Integer sales volume
- `region` — Sales region (North/South/East/West)
- `sale_date` — ISO 8601 date string
