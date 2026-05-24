import os
import sys
import traceback
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, render_template
from xgboost import XGBRanker

# Resolve all file paths relative to this script's directory
# so gunicorn finds them regardless of working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)

TRAIN_FILES = [
    os.path.join(BASE_DIR, "f1_2022.csv"),
    os.path.join(BASE_DIR, "f1_2023.csv"),
    os.path.join(BASE_DIR, "f1_2024.csv"),
    os.path.join(BASE_DIR, "f1_2025.csv"),
]
TEST_FILE = os.path.join(BASE_DIR, "f1_2026.csv")
GRID_WEIGHT = 1.0

# Global state to hold models, clean combined data, and encodings
models = {}
categories = {}
data_state = {
    "combined_clean": None,
    "train_df": None,
    "test_df": None,
}

BEFORE_FEATURES = [
    "driver_enc",
    "team_enc",
    "race_enc",
    "grid",
    "driver_form",
    "team_form",
    "finished",
    "grid_inv",
]

AFTER_FEATURES = [
    "driver_enc",
    "team_enc",
    "race_enc",
    "grid",
    "grid_inv",
    "grid_rank",
    "grid_norm",
    "is_pole",
    "front_row",
    "top3_grid",
    "top5_grid",
    "driver_form",
    "driver_win_rate",
    "team_form",
    "finished",
]


def load_data():
    train_df = pd.concat(
        [pd.read_csv(path) for path in TRAIN_FILES],
        ignore_index=True,
    )
    test_df = pd.read_csv(TEST_FILE)

    train_df["split"] = "train"
    test_df["split"] = "test"
    return train_df, test_df


def clean_data(df):
    clean = df.dropna(subset=["position"]).copy()
    clean = clean[clean["grid"] > 0].copy()
    return clean


def add_features(df, custom_grids=None):
    """
    Computes all historical and grid-based features.
    If custom_grids is provided as a dict of {driver: grid_position} for a specific race,
    it overrides the grids for that race and re-computes features.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "race_id", "position"]).reset_index(drop=True)

    df["grid"] = df["grid"].astype(float)
    
    # Apply custom grids if provided
    if custom_grids:
        for driver, custom_grid in custom_grids.items():
            mask = (df["driver"] == driver) & (df["split"] == "test")
            if mask.any():
                df.loc[mask, "grid"] = float(custom_grid)

    df["finished"] = (df["status"] == "Finished").astype(int)
    df["grid_inv"] = 1 / df["grid"]
    df["grid_rank"] = df.groupby("race_id")["grid"].rank(method="first")
    df["grid_norm"] = df["grid_rank"] / df.groupby("race_id")["grid"].transform("max")
    df["is_pole"] = (df["grid_rank"] == 1).astype(int)
    df["front_row"] = (df["grid_rank"] <= 2).astype(int)
    df["top3_grid"] = (df["grid_rank"] <= 3).astype(int)
    df["top5_grid"] = (df["grid_rank"] <= 5).astype(int)

    df["driver_form"] = (
        df.sort_values(["driver", "date", "race_id"])
        .groupby("driver")["position"]
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    )

    df["driver_win_rate"] = (
        df.sort_values(["driver", "date", "race_id"])
        .assign(is_win=lambda x: (x["position"] == 1).astype(int))
        .groupby("driver")["is_win"]
        .transform(lambda s: s.shift(1).rolling(10, min_periods=1).mean())
    )

    team_race_points = (
        df.groupby(["team", "date", "race_id"], as_index=False)["points"]
        .sum()
        .sort_values(["team", "date", "race_id"])
    )
    team_race_points["team_form"] = (
        team_race_points.groupby("team")["points"]
        .transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    )
    df = df.merge(
        team_race_points[["team", "date", "race_id", "team_form"]],
        on=["team", "date", "race_id"],
        how="left",
    )

    # Encode categories using the static list of categories mapped to consistent indices
    for col in ["driver", "team", "race"]:
        df[f"{col}_enc"] = df[col].map(
            lambda x, c=col: categories[c].index(x) if x in categories[c] else 0
        )

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def position_relevance(position):
    max_position = position.max()
    return (max_position - position + 1).astype(int)


def winner_relevance(position):
    return (position == 1).astype(int)


def init_models():
    print("Initializing and training models...", flush=True)
    print(f"BASE_DIR: {BASE_DIR}", flush=True)
    print(f"CSV files: {TRAIN_FILES + [TEST_FILE]}", flush=True)

    train_raw, test_raw = load_data()
    print(f"Data loaded — train: {len(train_raw)} rows, test: {len(test_raw)} rows", flush=True)

    # Store raw test dataset to fetch races and initial layouts easily
    data_state["test_raw"] = test_raw.copy()

    # Clean only complete races for training and baseline evaluation
    train_clean = clean_data(train_raw)
    test_clean = clean_data(test_raw)

    combined_clean = pd.concat([train_clean, test_clean], ignore_index=True)

    # Build reference category encoders from ALL data (including upcoming races
    # in test_raw) so that new drivers/teams/races are always known.
    all_data = pd.concat([train_raw, test_raw], ignore_index=True)
    for col in ["driver", "team", "race"]:
        categories[col] = sorted(all_data[col].dropna().unique())

    # Store the RAW cleaned combined data (before feature engineering).
    # This is used as the historical base when building features for
    # upcoming or custom-grid races, avoiding double-engineering bugs.
    data_state["combined_clean_raw"] = combined_clean.copy()

    # Build features on cleaned combined data
    combined_clean_feat = add_features(combined_clean)

    train_df = combined_clean_feat[combined_clean_feat["split"] == "train"].copy()
    test_df = combined_clean_feat[combined_clean_feat["split"] == "test"].copy()

    data_state["combined_clean"] = combined_clean_feat
    data_state["train_df"] = train_df
    data_state["test_df"] = test_df

    # Train Before Qualifying Model
    X_train_before = train_df[BEFORE_FEATURES]
    y_train_before = train_df.groupby("race_id", sort=False)["position"].transform(position_relevance)
    group_train = train_df.groupby("race_id", sort=False).size().values

    model_before = XGBRanker(
        objective="rank:pairwise",
        learning_rate=0.1,
        n_estimators=200,
        max_depth=6,
        eval_metric="ndcg",
    )
    model_before.fit(
        X_train_before,
        y_train_before,
        group=group_train,
        verbose=False,
    )
    models["before"] = model_before
    print("Before-qualifying model trained.", flush=True)

    # Train After Qualifying Model
    X_train_after = train_df[AFTER_FEATURES]
    y_train_after = winner_relevance(train_df["position"])

    model_after = XGBRanker(
        objective="rank:pairwise",
        learning_rate=0.05,
        n_estimators=300,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="ndcg",
        random_state=42,
    )
    model_after.fit(
        X_train_after,
        y_train_after,
        group=group_train,
        verbose=False,
    )
    models["after"] = model_after
    print("Models trained successfully!", flush=True)


# Train models on start
try:
    init_models()
except Exception as e:
    print(f"FATAL: Failed to initialize models: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/races', methods=['GET'])
def get_races():
    """
    Returns list of 2025 races, dates, completed/upcoming status, and actual winners.
    """
    test_raw = data_state["test_raw"]
    races_summary = []
    
    # Group by race_id to get race-level details
    for race_id in sorted(test_raw["race_id"].unique(), key=lambda r: int(r.split('_')[1])):
        race_subset = test_raw[test_raw["race_id"] == race_id]
        race_name = race_subset["race"].iloc[0]
        race_date = pd.to_datetime(race_subset["date"].iloc[0]).date().isoformat()
        
        # Check if actual results are filled (completed)
        completed = not race_subset["position"].isna().all()
        actual_winner = None
        if completed:
            winner_row = race_subset[race_subset["position"] == 1]
            if not winner_row.empty:
                actual_winner = winner_row["driver"].iloc[0]
                
        races_summary.append({
            "race_id": race_id,
            "race": race_name,
            "date": race_date,
            "completed": completed,
            "actual_winner": actual_winner
        })
        
    return jsonify(races_summary)


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """
    Returns overall model evaluation accuracies.
    """
    test_df = data_state["test_df"].copy()
    
    # Generate predictions for the test dataset
    X_test_before = test_df[BEFORE_FEATURES]
    X_test_after = test_df[AFTER_FEATURES]
    
    test_df["before_score"] = models["before"].predict(X_test_before)
    test_df["after_model_score"] = models["after"].predict(X_test_after)
    test_df["after_score"] = test_df["after_model_score"] + (GRID_WEIGHT * test_df["grid_inv"])
    
    before_correct = 0
    after_correct = 0
    total = 0
    top3_overlap_after = 0
    
    comparison_rows = []
    
    for race_id in test_df["race_id"].unique():
        race = test_df[test_df["race_id"] == race_id]
        
        # Before qualifying predictions
        pred_before = race.sort_values("before_score", ascending=False).iloc[0]["driver"]
        
        # After qualifying predictions
        pred_after_sorted = race.sort_values("after_score", ascending=False)
        pred_after = pred_after_sorted.iloc[0]["driver"]
        pred_top3 = set(pred_after_sorted.head(3)["driver"])
        
        actual_sorted = race.sort_values("position")
        actual_winner = actual_sorted.iloc[0]["driver"]
        actual_top3 = set(actual_sorted.head(3)["driver"])
        
        if pred_before == actual_winner:
            before_correct += 1
        if pred_after == actual_winner:
            after_correct += 1
            
        top3_overlap_after += len(pred_top3 & actual_top3)
        total += 1
        
        comparison_rows.append({
            "race_id": race_id,
            "race": race["race"].iloc[0],
            "actual_winner": actual_winner,
            "before_prediction": pred_before,
            "before_correct": pred_before == actual_winner,
            "after_prediction": pred_after,
            "after_correct": pred_after == actual_winner
        })
        
    return jsonify({
        "before_accuracy": before_correct / total if total > 0 else 0,
        "after_accuracy": after_correct / total if total > 0 else 0,
        "after_top3_avg_overlap": top3_overlap_after / total if total > 0 else 0,
        "total_races": total,
        "comparisons": comparison_rows
    })


@app.route('/api/race_details/<race_id>', methods=['GET'])
def get_race_details(race_id):
    """
    Returns full predictions and grid lists for a specific race.
    """
    # First check if the race was completed in our clean test set
    test_df = data_state["test_df"]
    race_feat = test_df[test_df["race_id"] == race_id]
    
    completed = True
    if race_feat.empty:
        # It's an upcoming/incomplete race! Let's load it from test_raw and build features.
        completed = False
        test_raw = data_state["test_raw"]
        race_raw = test_raw[test_raw["race_id"] == race_id].copy()
        if race_raw.empty:
            return jsonify({"error": f"Race {race_id} not found."}), 404

        # Compute championship standings from completed 2026 races to
        # generate a meaningful default grid when qualifying is unknown.
        completed_test = data_state["combined_clean_raw"][
            data_state["combined_clean_raw"]["split"] == "test"
        ]
        if not completed_test.empty:
            standings = (
                completed_test.groupby("driver")["points"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            standings["standing_grid"] = range(1, len(standings) + 1)
            standing_map = dict(
                zip(standings["driver"], standings["standing_grid"])
            )
        else:
            standing_map = {}

        # Assign grid: use existing grid from CSV if valid, otherwise use
        # championship standing order.  Fall back to 20 for unknown drivers.
        race_raw["grid"] = race_raw.apply(
            lambda row: (
                float(row["grid"])
                if pd.notna(row["grid"]) and float(row["grid"]) > 0
                else float(standing_map.get(row["driver"], 20))
            ),
            axis=1,
        )

        # Use a very high dummy position so the upcoming race doesn't
        # artificially look like a good or bad finish in form calculations.
        # We'll mark it and exclude it from form later via the position value.
        race_raw["position"] = race_raw["position"].fillna(20.0)
        race_raw["points"] = race_raw["points"].fillna(0.0)
        race_raw["status"] = race_raw["status"].fillna("Finished")

        # Combine RAW clean historical data with this single race to build
        # forms correctly.  We must NOT use the already-feature-engineered
        # train_df here, because add_features() would double-process it and
        # create duplicate columns (e.g. team_form_x / team_form_y).
        temp_combined = pd.concat(
            [data_state["combined_clean_raw"], race_raw], ignore_index=True
        )
        temp_combined_feat = add_features(temp_combined)
        race_feat = temp_combined_feat[temp_combined_feat["race_id"] == race_id].copy()

    # Generate predictions
    X_before = race_feat[BEFORE_FEATURES]
    X_after = race_feat[AFTER_FEATURES]
    
    race_feat = race_feat.copy()
    race_feat["before_score"] = models["before"].predict(X_before)
    race_feat["after_model_score"] = models["after"].predict(X_after)
    race_feat["after_score"] = race_feat["after_model_score"] + (GRID_WEIGHT * race_feat["grid_inv"])
    
    # Sort before qualifying predictions
    before_ranked = race_feat.sort_values("before_score", ascending=False)
    before_order = {row["driver"]: i+1 for i, (_, row) in enumerate(before_ranked.iterrows())}
    
    # Sort after qualifying predictions
    after_ranked = race_feat.sort_values("after_score", ascending=False)
    after_order = {row["driver"]: i+1 for i, (_, row) in enumerate(after_ranked.iterrows())}
    
    results = []
    for _, row in race_feat.iterrows():
        driver = row["driver"]
        results.append({
            "driver": driver,
            "team": row["team"],
            "grid": int(row["grid"]),
            "actual_position": int(row["position"]) if completed and row["position"] <= 22 else None,
            "before_score": float(row["before_score"]),
            "before_rank": before_order[driver],
            "after_score": float(row["after_score"]),
            "after_rank": after_order[driver],
            "driver_form": float(row["driver_form"]),
            "team_form": float(row["team_form"])
        })
        
    # Sort results by actual position (or grid if not completed)
    results = sorted(results, key=lambda x: x["actual_position"] if completed and x["actual_position"] else x["grid"])
    
    return jsonify({
        "race_id": race_id,
        "race": race_feat["race"].iloc[0],
        "date": pd.to_datetime(race_feat["date"].iloc[0]).date().isoformat(),
        "completed": completed,
        "drivers": results
    })


@app.route('/api/predict_custom', methods=['POST'])
def predict_custom():
    """
    Accepts customized grid list:
    {
      "race_id": "2025_5",
      "grids": {
         "VER": 1,
         "NOR": 2,
         ...
      }
    }
    Recalculates features and returns the updated ranking.
    """
    req_data = request.get_json() or {}
    race_id = req_data.get("race_id")
    custom_grids = req_data.get("grids")
    
    if not race_id or not custom_grids:
        return jsonify({"error": "race_id and grids are required fields."}), 400
        
    test_raw = data_state["test_raw"]
    race_raw = test_raw[test_raw["race_id"] == race_id].copy()
    if race_raw.empty:
        return jsonify({"error": f"Race {race_id} not found."}), 404

    # Apply the user-supplied custom grids to the race rows
    for driver, custom_grid in custom_grids.items():
        mask = race_raw["driver"] == driver
        if mask.any():
            race_raw.loc[mask, "grid"] = float(custom_grid)

    # Standardize missing values for upcoming races
    race_raw["grid"] = race_raw["grid"].fillna(20.0).astype(float)
    race_raw["position"] = race_raw["position"].fillna(20.0)
    race_raw["points"] = race_raw["points"].fillna(0.0)
    race_raw["status"] = race_raw["status"].fillna("Finished")

    # Build RAW clean historical data + this race raw.
    # Must use combined_clean_raw (not the feature-engineered train_df)
    # to avoid duplicate columns when add_features runs the team_form merge.
    temp_combined = pd.concat(
        [data_state["combined_clean_raw"], race_raw], ignore_index=True
    )
    
    # Recalculate features (custom grids already applied to race_raw above)
    temp_combined_feat = add_features(temp_combined)
    race_feat = temp_combined_feat[temp_combined_feat["race_id"] == race_id].copy()

    # Generate predictions
    X_before = race_feat[BEFORE_FEATURES]
    X_after = race_feat[AFTER_FEATURES]
    
    race_feat = race_feat.copy()
    race_feat["before_score"] = models["before"].predict(X_before)
    race_feat["after_model_score"] = models["after"].predict(X_after)
    race_feat["after_score"] = race_feat["after_model_score"] + (GRID_WEIGHT * race_feat["grid_inv"])
    
    # Sort before qualifying predictions
    before_ranked = race_feat.sort_values("before_score", ascending=False)
    before_order = {row["driver"]: i+1 for i, (_, row) in enumerate(before_ranked.iterrows())}
    
    # Sort after qualifying predictions
    after_ranked = race_feat.sort_values("after_score", ascending=False)
    after_order = {row["driver"]: i+1 for i, (_, row) in enumerate(after_ranked.iterrows())}
    
    results = []
    for _, row in race_feat.iterrows():
        driver = row["driver"]
        results.append({
            "driver": driver,
            "team": row["team"],
            "grid": int(row["grid"]),
            "before_score": float(row["before_score"]),
            "before_rank": before_order[driver],
            "after_score": float(row["after_score"]),
            "after_rank": after_order[driver],
            "driver_form": float(row["driver_form"]),
            "team_form": float(row["team_form"])
        })
        
    # Sort results by the newly predicted after-qualifying order
    results = sorted(results, key=lambda x: x["after_rank"])
    
    return jsonify({
        "race_id": race_id,
        "race": race_feat["race"].iloc[0],
        "drivers": results
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('RENDER') is None  # disable debug on Render
    app.run(debug=debug, host='0.0.0.0', port=port)
