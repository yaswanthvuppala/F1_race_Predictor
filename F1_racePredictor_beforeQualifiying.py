import numpy as np
import pandas as pd
from xgboost import XGBRanker


TRAIN_FILES = ["f1_2022.csv", "f1_2023.csv", "f1_2024.csv"]
TEST_FILE = "f1_2025.csv"


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

    df["finished"] = (df["status"] == "Finished").astype(int)
    df["grid_inv"] = 1 / df["grid"]

    df["driver_form"] = (
        df.sort_values(["driver", "date", "race_id"])
        .groupby("driver")["position"]
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
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


def relevance_from_position(position):
    max_position = position.max()
    return (max_position - position + 1).astype(int)


train_raw, test_raw = load_data()
train_clean, train_dropped = clean_data(train_raw)
test_clean, test_dropped = clean_data(test_raw)

combined = pd.concat([train_clean, test_clean], ignore_index=True)
combined = add_features(combined)

train_df = combined[combined["split"] == "train"].copy()
test_df = combined[combined["split"] == "test"].copy()

print("Data loaded")
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
    "driver_form",
    "team_form",
    "finished",
    "grid_inv",
]

X_train = train_df[features]
y_train = train_df.groupby("race_id", sort=False)["position"].transform(relevance_from_position)

X_test = test_df[features]
y_test = test_df.groupby("race_id", sort=False)["position"].transform(relevance_from_position)

group_train = train_df.groupby("race_id", sort=False).size().values
group_test = test_df.groupby("race_id", sort=False).size().values

assert group_train.sum() == len(X_train), "Group/row mismatch in train!"
assert group_test.sum() == len(X_test), "Group/row mismatch in test!"

model = XGBRanker(
    objective="rank:pairwise",
    learning_rate=0.1,
    n_estimators=200,
    max_depth=6,
    eval_metric="ndcg",
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

test_df["score"] = model.predict(X_test)

correct = 0
total = 0

for race_id in test_df["race_id"].unique():
    race = test_df[test_df["race_id"] == race_id]
    pred = race.sort_values("score", ascending=False)
    actual = race.sort_values("position")

    if pred.iloc[0]["driver"] == actual.iloc[0]["driver"]:
        correct += 1
    total += 1

if total == 0:
    raise ValueError("No completed 2025 races were available for evaluation.")

print(f"\nWinner Accuracy: {correct}/{total} = {correct / total:.2%}")

total_overlap = 0

for race_id in test_df["race_id"].unique():
    race = test_df[test_df["race_id"] == race_id]
    pred_top10 = set(race.sort_values("score", ascending=False).head(10)["driver"])
    actual_top10 = set(race.nsmallest(10, "position")["driver"])
    total_overlap += len(pred_top10 & actual_top10)

print(f"Avg Top-10 Overlap: {total_overlap / total:.2f} / 10")

print("\nPer-Race Predictions")
for race_id in test_df["race_id"].unique():
    race = test_df[test_df["race_id"] == race_id]
    race_name = race["race"].iloc[0]
    pred_win = race.sort_values("score", ascending=False).iloc[0]["driver"]
    actual_win = race.sort_values("position").iloc[0]["driver"]
    match = "OK" if pred_win == actual_win else "MISS"
    print(f"{match:4s} {race_name:35s}  Predicted: {pred_win:4s}  Actual: {actual_win}")
