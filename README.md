# F1 Race Predictor

This repository contains Formula 1 race prediction models trained on 2022-2024 race data and evaluated on completed 2025 races.

## Files

- `F1_racePredictor_beforeQualifiying.py` trains a ranking model for race result prediction.
- `F1_racepredictor_AfterQyualifiying.py` trains a grid-aware winner model that adds qualifying/grid-position features.
- `compare_f1_predictors.py` runs both approaches on the same 2025 test data and creates a graphical comparison.
- `f1_2022.csv`, `f1_2023.csv`, `f1_2024.csv`, and `f1_2025.csv` contain the race result data.

## Setup

Install the Python packages used by the predictors:

```bash
pip install pandas numpy xgboost matplotlib
```

## Run The Predictors

Before-qualifying style predictor:

```bash
python F1_racePredictor_beforeQualifiying.py
```

After-qualifying grid-aware predictor:

```bash
python F1_racepredictor_AfterQyualifiying.py
```

Compare both models graphically:

```bash
python compare_f1_predictors.py
```

The comparison script creates:

- `f1_predictor_comparison.png`
- `f1_predictor_comparison.csv`

## Data Split

The models train on:

- `f1_2022.csv`
- `f1_2023.csv`
- `f1_2024.csv`

The models test on:

- `f1_2025.csv`

Rows with missing finishing positions are treated as incomplete race data and excluded from test evaluation.
