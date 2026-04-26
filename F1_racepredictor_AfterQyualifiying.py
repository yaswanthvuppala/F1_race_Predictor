import numpy as np
import pandas as pd
from xgboost import XGBRanker


TRAIN_FILES = ["f1_2022.csv", "f1_2023.csv", "f1_2024.csv"]
TEST_FILE = "f1_2025.csv"
GRID_WEIGHT = 5.0


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
    before = len(df)
    clean = df.dropna(subset=["position"]).copy()
    clean = clean[clean["grid"] > 0].copy()
    return clean, before - len(clean)


def add_features(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "race_id", "position"]).reset_index(drop=True)

    df["grid"] = df["grid"].astype(float)
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

    for col in ["driver", "team", "race"]:
        df[f"{col}_enc"], _ = pd.factorize(df[col], sort=True)

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def winner_relevance(position):
    return (position == 1).astype(int)


train_raw, test_raw = load_data()
train_clean, train_dropped = clean_data(train_raw)
test_clean, test_dropped = clean_data(test_raw)

combined = pd.concat([train_clean, test_clean], ignore_index=True)
combined = add_features(combined)

train_df = combined[combined["split"] == "train"].copy()
test_df = combined[combined["split"] == "test"].copy()

print("F1 winner model")
print(f"Train files: {', '.join(TRAIN_FILES)}")
print(f"Test file:  {TEST_FILE}")
print(f"Train rows dropped during cleaning: {train_dropped}")
print(f"2025 test rows dropped during cleaning: {test_dropped}")
print(f"Train races: {train_df['race_id'].nunique()} | Test races: {test_df['race_id'].nunique()}")
print(f"Train rows:  {len(train_df)}  | Test rows:  {len(test_df)}")

features = [
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
]

X_train = train_df[features]
y_train = winner_relevance(train_df["position"])

X_test = test_df[features]
y_test = winner_relevance(test_df["position"])

group_train = train_df.groupby("race_id", sort=False).size().values
group_test = test_df.groupby("race_id", sort=False).size().values

assert group_train.sum() == len(X_train), "Group/row mismatch in train!"
assert group_test.sum() == len(X_test), "Group/row mismatch in test!"

model = XGBRanker(
    objective="rank:pairwise",
    learning_rate=0.05,
    n_estimators=300,
    max_depth=4,
    subsample=0.9,
    colsample_bytree=0.9,
    eval_metric="ndcg",
    random_state=42,
)

model.fit(
    X_train,
    y_train,
    group=group_train,
    eval_set=[(X_test, y_test)],
    eval_group=[group_test],
    verbose=False,
)

print("Model trained successfully")
print(f"Final winner score: model_score + {GRID_WEIGHT} * grid_inv")

test_df["model_score"] = model.predict(X_test)
test_df["win_score"] = test_df["model_score"] + (GRID_WEIGHT * test_df["grid_inv"])

correct = 0
total = 0

print("\nPer-Race Winner Predictions")
for race_id in test_df["race_id"].unique():
    race = test_df[test_df["race_id"] == race_id]
    pred = race.sort_values("win_score", ascending=False)
    actual = race.sort_values("position")

    pred_row = pred.iloc[0]
    actual_row = actual.iloc[0]
    match = "OK" if pred_row["driver"] == actual_row["driver"] else "MISS"

    if match == "OK":
        correct += 1
    total += 1

    print(
        f"{match:4s} {race['race'].iloc[0]:35s}  "
        f"Predicted: {pred_row['driver']:4s} Grid: {int(pred_row['grid']):2d}  "
        f"Actual: {actual_row['driver']:4s} Grid: {int(actual_row['grid']):2d}"
    )

if total == 0:
    raise ValueError("No completed 2025 races were available for evaluation.")

print(f"\nWinner Accuracy: {correct}/{total} = {correct / total:.2%}")

total_top3 = 0
for race_id in test_df["race_id"].unique():
    race = test_df[test_df["race_id"] == race_id]
    predicted_top3 = set(race.sort_values("win_score", ascending=False).head(3)["driver"])
    actual_winner = race.sort_values("position").iloc[0]["driver"]
    total_top3 += int(actual_winner in predicted_top3)

print(f"Winner in Predicted Top 3: {total_top3}/{total} = {total_top3 / total:.2%}")
