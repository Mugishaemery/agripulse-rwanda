# AgriPulse Rwanda
**Data-Driven Agricultural Productivity and Risk Intelligence** - NISR Big Data Hackathon 2026, Track 1 (Agricultural Productivity).

## Overview
AgriPulse turns NISR Seasonal Agricultural Survey (SAS) 2024 data into district comparisons, a yield estimator and a transparent productivity-risk view for agricultural planners.

## Problem
Yields differ widely across Rwanda's districts, crops and seasons. Planners need to see where productivity lags and what to investigate, but survey tables are hard to use.

## Solution
Official NISR district tables power an interactive dashboard, map, crop analysis and risk ranking. A model trained on plot-level SAS microdata estimates yield for a plot, with an honest error range.

## Key features
Dashboard - Map (Leaflet) - Crop analysis - Yield prediction - Risk and intervention intelligence - Methodology page.

## Data source
NISR SAS 2024: published *Annual Tables* (district level) and public-use microdata (plot level). **The microdata is not included in this repository** (NISR terms: no redistribution). Cite: National Institute of Statistics of Rwanda, Seasonal Agricultural Survey 2024.

## Technology stack
HTML/CSS/JS, Bootstrap 5, Chart.js, Leaflet - Node.js + Express REST API - ML in Python (numpy/pandas), exported to JSON and evaluated in Node (no Python needed at run time).
*Database:* `database/schema.sql` is a **planned** MySQL schema. The current build serves processed JSON files so it deploys without a database; a MySQL loader is future work.

## Machine learning methodology
See `docs/methodology.md`. Target = log yield; pre-harvest features only; split by survey segment; Linear Regression, Random Forest, Gradient Boosting compared with a crop x season benchmark.

## Model evaluation (held-out plots: 8,196 plots from segments unseen in training; 28,027 train)
| Model | MAE kg/ha | Median % error | R2 (log) |
|---|---|---|---|
| Benchmark (crop x season median) | 1,262 | 36.3% | 0.665 |
| Linear Regression | 1,249 | 36.3% | 0.698 |
| Random Forest | 1,181 | 35.1% | 0.721 |
| **Gradient Boosting (selected)** | 1,187 | 35.0% | 0.722 |
| Gradient Boosting (regularized) | 1,224 | 35.8% | 0.708 |

The model improves on the benchmark only modestly (it helps for maize, sorghum, paddy rice, soybean, pea; it does not for bean, vegetables, groundnuts). Crop is by far the most important factor, then district, improved seed, area, season. Importance is not causation.

## Installation and running
```bash
npm install
cp .env.example .env
npm start        # http://localhost:3000
```
Rebuild real data (needs the NISR files, not in the repo): `python ml/preprocessing/build_aggregates.py`, `python ml/preprocessing/build_microdata.py`, `python ml/models/train_models.py`.

## API
`GET /api/overview, /districts, /crops, /seasons, /productivity, /productivity/district/:d, /productivity/crop/:c, /inputs, /map, /risk, /model/performance, /model/features, /model/options` - `POST /api/predict`.

## Project structure
`frontend/` pages - `backend/` Express API and services - `ml/` preprocessing and training - `data/processed/aggregates.json` published NISR tables - `ml/models/` exported model and metrics - `docs/` methodology - `database/` planned schema.

## Limitations
Observational data; no causal claims. Plot yield depends on factors the survey does not record before harvest. Perennial crops are not modelled. Season B crop areas are partly estimated. See `docs/methodology.md`.

## Future improvements
MySQL loader; rainfall and soil data as extra predictors; district-level forecasting; validated risk thresholds.

## Team
TODO: add the two team members and universities.

## Hackathon
2026 NISR Big Data Hackathon, Track 1: Agricultural Productivity.

## AI tool disclosure
AI assistance (Claude, by Anthropic) was used for code, analysis and documentation drafting. The team reviewed the work and is responsible for it.
