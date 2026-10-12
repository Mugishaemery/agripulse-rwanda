# Methodology

## Data
1. **Published district tables** - NISR *Seasonal Agricultural Survey 2024, Annual Tables* (district x crop area, production, yield; district input-use shares). Drives the dashboard, map, crops and risk pages. District sums reproduce NISR national totals exactly (e.g. maize Season A cultivated area 249,435 ha; production 507,985 t).
2. **Plot-level microdata** - NISR SAS 2024 public-use files (Seasons A, B, C). Used only to train the yield model. The microdata is **not** redistributed: it is excluded from the repository and the deployed site.

## Yield definition
yield (kg/ha) = crop production (kg) / crop area (ha), as defined in the SAS report. Aggregates use total production / total harvested area. Plot-level target: `s2q21` (harvest of the crop on the plot) / `crop_area` (Screening table). Validation: survey-weighted microdata yields were compared with NISR's published yields; they agree closely for annual crops (e.g. beans A 691 vs 709 kg/ha, Irish potato A 8,809 vs 8,541). The other harvest variable (`s2q22`) gave yields 2-4x too high and was rejected.

## Cleaning
- Production joined to Screening on segment, farmer, plot and crop. Fodder crops and lemongrass excluded from the food-crop groups; tree tomato treated as a fruit.
- Rows with no harvest value (crop not yet harvested) and rows with no crop area are removed.
- Yield outliers removed with a robust rule (4 x MAD on log yield within crop x season); 338 of 70,972 rows.
- Plot-level yes/no answers blank because the farm-level gate question was "No" are set to 0 (counts match exactly).
- **Season B:** Screening lists different crops from Production, so 57% of crop areas are missing. Missing areas were estimated as plot area / number of crops on the plot (unbiased overall, median ratio 0.98-1.00, but noisy per plot: ~30% of rows differ by more than 2x). The model is trained on plots with a **measured** crop area; the full set is a sensitivity check.
- **Perennials** (banana, cassava, fruits) are excluded from the model: NISR's published yields divide by harvested area, which is smaller than the planted area used here, so microdata yields were 30-50% lower than published.

## Model
- Target: log(yield). Features (pre-harvest only): district, crop, season, area under the crop, erosion degree, cropping system, inorganic fertilizer rate band, improved seed, organic fertilizer, pesticide, anti-erosion measures, irrigation, mechanization, land consolidation.
- Leakage control: no harvest, sales, storage or loss variables used as inputs.
- Split: 80/20 **by survey segment**, so plots from one segment are never in both sets.
- Models: Linear Regression, Random Forest, Gradient Boosting, a regularized Gradient Boosting, and a benchmark (median yield of the same crop and season). Implemented in numpy (no SciPy/scikit-learn), checked against scikit-learn on test data. Selection by log-scale R2 on held-out plots (raw-scale RMSE is dominated by a few extreme plots).

## Risk index (rule-based, not ML)
index = observed production / expected production, expected = harvested area x national yield of the same crop and season. HIGH < 0.90, MEDIUM < 1.00, otherwise LOW. Thresholds are provisional. "Observed differences" compare a district's input use and erosion with the district average and are associations, not causes.

## Limitations
Observational data: no causal claims. Plot yield depends on rainfall, soil, pests and management not recorded before harvest; the model improves only modestly on a crop-and-season benchmark and is worse than it for some crops (the app says so per crop). District averages hide farm-level differences. Season C is small. Input-vs-productivity comparisons use 30 districts.
