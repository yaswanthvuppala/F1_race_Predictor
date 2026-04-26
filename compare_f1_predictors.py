import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBRanker


TRAIN_FILES = ["f1_2022.csv", "f1_2023.csv", "f1_2024.csv"]
TEST_FILE = "f1_2025.csv"
GRID_WEIGHT = 5.0
OUTPUT_CHART = "f1_predictor_comparison.png"
OUTPUT_TABLE = "f1_predictor_comparison.csv"


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
    before = len(df)
    clean = df.dropna(subset=["position"]).copy()
    clean = clean[clean["grid"] > 0].copy()
    return clean, before - len(clean)


def add_features(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "race_id", "position"]).reset_index(drop=True)

    df["grid"] = df["grid"].astype(float)
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

    for col in ["driver", "team", "race"]:
        df[f"{col}_enc"], _ = pd.factorize(df[col], sort=True)

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def position_relevance(position):
    max_position = position.max()
    return (max_position - position + 1).astype(int)


def winner_relevance(position):
    return (position == 1).astype(int)


def train_ranker(train_df, test_df, features, target, params):
    X_train = train_df[features]
    X_test = test_df[features]
    group_train = train_df.groupby("race_id", sort=False).size().values
    group_test = test_df.groupby("race_id", sort=False).size().values

    assert group_train.sum() == len(X_train), "Group/row mismatch in train!"
    assert group_test.sum() == len(X_test), "Group/row mismatch in test!"

    y_train = target(train_df)
    y_test = winner_relevance(test_df["position"])

    model = XGBRanker(**params)
    model.fit(
        X_train,
        y_train,
        group=group_train,
        eval_set=[(X_test, y_test)],
        eval_group=[group_test],
        verbose=False,
    )
    return model.predict(X_test)


def evaluate(test_df, score_col):
    rows = []
    correct = 0
    winner_in_top3 = 0

    for race_id in test_df["race_id"].unique():
        race = test_df[test_df["race_id"] == race_id]
        ranked = race.sort_values(score_col, ascending=False)
        actual = race.sort_values("position").iloc[0]
        predicted = ranked.iloc[0]

        is_correct = predicted["driver"] == actual["driver"]
        in_top3 = actual["driver"] in set(ranked.head(3)["driver"])
        correct += int(is_correct)
        winner_in_top3 += int(in_top3)

        rows.append(
            {
                "race_id": race_id,
                "race": race["race"].iloc[0],
                "date": actual["date"].date().isoformat(),
                "predicted_driver": predicted["driver"],
                "predicted_grid": int(predicted["grid"]),
                "actual_driver": actual["driver"],
                "actual_grid": int(actual["grid"]),
                "correct": is_correct,
                "winner_in_top3": in_top3,
            }
        )

    total = len(rows)
    return {
        "winner_accuracy": correct / total,
        "top3_accuracy": winner_in_top3 / total,
        "correct": correct,
        "top3_correct": winner_in_top3,
        "total": total,
        "rows": rows,
    }


def plot_results(before, after, comparison_df):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("F1 Race Predictor Comparison on 2025 Test Data", fontsize=16, fontweight="bold")

    labels = ["Winner Accuracy", "Winner in Top 3"]
    before_values = [before["winner_accuracy"] * 100, before["top3_accuracy"] * 100]
    after_values = [after["winner_accuracy"] * 100, after["top3_accuracy"] * 100]

    x = np.arange(len(labels))
    width = 0.34
    axes[0].bar(x - width / 2, before_values, width, label="Before qualifying", color="#4f6d7a")
    axes[0].bar(x + width / 2, after_values, width, label="After qualifying", color="#e10600")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylim(0, 110)
    axes[0].set_ylabel("Accuracy (%)")
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.25)

    race_labels = comparison_df["race"].str.replace(" Grand Prix", "", regex=False)
    y = np.arange(len(race_labels))
    axes[1].scatter(
        comparison_df["before_correct"].astype(int),
        y,
        label="Before qualifying",
        color="#4f6d7a",
        s=70,
    )
    axes[1].scatter(
        comparison_df["after_correct"].astype(int) + 0.05,
        y,
        label="After qualifying",
        color="#e10600",
        s=70,
    )
    axes[1].set_yticks(y, race_labels)
    axes[1].set_xticks([0, 1], ["Miss", "Correct"])
    axes[1].set_xlim(-0.25, 1.25)
    axes[1].set_title("Per-race winner prediction")
    axes[1].legend()
    axes[1].grid(axis="x", alpha=0.25)

    plt.tight_layout()
    fig.savefig(OUTPUT_CHART, dpi=160)
    plt.close(fig)


def main():
    train_raw, test_raw = load_data()
    train_clean, train_dropped = clean_data(train_raw)
    test_clean, test_dropped = clean_data(test_raw)

    combined = pd.concat([train_clean, test_clean], ignore_index=True)
    combined = add_features(combined)
    train_df = combined[combined["split"] == "train"].copy()
    test_df = combined[combined["split"] == "test"].copy()

    before_scores = train_ranker(
        train_df,
        test_df,
        BEFORE_FEATURES,
        lambda df: df.groupby("race_id", sort=False)["position"].transform(position_relevance),
        {
            "objective": "rank:pairwise",
            "learning_rate": 0.1,
            "n_estimators": 200,
            "max_depth": 6,
            "eval_metric": "ndcg",
        },
    )
    after_scores = train_ranker(
        train_df,
        test_df,
        AFTER_FEATURES,
        lambda df: winner_relevance(df["position"]),
        {
            "objective": "rank:pairwise",
            "learning_rate": 0.05,
            "n_estimators": 300,
            "max_depth": 4,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "eval_metric": "ndcg",
            "random_state": 42,
        },
    )

    test_df["before_score"] = before_scores
    test_df["after_score"] = after_scores + (GRID_WEIGHT * test_df["grid_inv"])

    before = evaluate(test_df, "before_score")
    after = evaluate(test_df, "after_score")

    before_df = pd.DataFrame(before["rows"]).add_prefix("before_")
    after_df = pd.DataFrame(after["rows"]).add_prefix("after_")
    comparison_df = pd.DataFrame(
        {
            "race": before_df["before_race"],
            "date": before_df["before_date"],
            "actual_winner": before_df["before_actual_driver"],
            "actual_grid": before_df["before_actual_grid"],
            "before_prediction": before_df["before_predicted_driver"],
            "before_grid": before_df["before_predicted_grid"],
            "before_correct": before_df["before_correct"],
            "after_prediction": after_df["after_predicted_driver"],
            "after_grid": after_df["after_predicted_grid"],
            "after_correct": after_df["after_correct"],
        }
    )
    comparison_df.to_csv(OUTPUT_TABLE, index=False)
    plot_results(before, after, comparison_df)

    print("F1 predictor comparison complete")
    print(f"Train rows dropped: {train_dropped}")
    print(f"2025 test rows dropped: {test_dropped}")
    print(
        f"Before qualifying winner accuracy: "
        f"{before['correct']}/{before['total']} = {before['winner_accuracy']:.2%}"
    )
    print(
        f"After qualifying winner accuracy: "
        f"{after['correct']}/{after['total']} = {after['winner_accuracy']:.2%}"
    )
    print(f"Saved chart: {OUTPUT_CHART}")
    print(f"Saved table: {OUTPUT_TABLE}")


if __name__ == "__main__":
    main()
