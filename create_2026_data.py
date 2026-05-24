import csv

# 2026 driver/team pairings
DRIVERS_TEAMS = [
    ("RUS", "Mercedes"),
    ("ANT", "Mercedes"),
    ("LEC", "Ferrari"),
    ("HAM", "Ferrari"),
    ("NOR", "McLaren"),
    ("PIA", "McLaren"),
    ("VER", "Red Bull Racing"),
    ("HAD", "Red Bull Racing"),
    ("ALO", "Aston Martin"),
    ("STR", "Aston Martin"),
    ("ALB", "Williams"),
    ("SAI", "Williams"),
    ("GAS", "Alpine"),
    ("COL", "Alpine"),
    ("OCO", "Haas F1 Team"),
    ("BEA", "Haas F1 Team"),
    ("LAW", "Racing Bulls"),
    ("LIN", "Racing Bulls"),
    ("HUL", "Audi"),
    ("BOR", "Audi"),
    ("PER", "Cadillac"),
    ("BOT", "Cadillac"),
]

RACES = [
    # completed races
    ("2026_1", "Australian Grand Prix", "2026-03-08", True),
    ("2026_2", "Chinese Grand Prix", "2026-03-15", True),
    ("2026_3", "Japanese Grand Prix", "2026-03-29", True),
    ("2026_6", "Miami Grand Prix", "2026-05-03", True),
    # today's race - grid is known, results not finished
    ("2026_7", "Canadian Grand Prix", "2026-05-24", False),
    # upcoming races
    ("2026_8", "Monaco Grand Prix", "2026-06-07", False),
    ("2026_9", "Spanish Grand Prix", "2026-06-14", False),
    ("2026_10", "Austrian Grand Prix", "2026-06-28", False),
    ("2026_11", "British Grand Prix", "2026-07-05", False),
    ("2026_12", "Belgian Grand Prix", "2026-07-19", False),
    ("2026_13", "Hungarian Grand Prix", "2026-07-26", False),
    ("2026_14", "Dutch Grand Prix", "2026-08-23", False),
    ("2026_15", "Italian Grand Prix", "2026-09-06", False),
    ("2026_16", "Madrid Grand Prix", "2026-09-13", False),
    ("2026_17", "Azerbaijan Grand Prix", "2026-09-26", False),
    ("2026_18", "Singapore Grand Prix", "2026-10-11", False),
    ("2026_19", "United States Grand Prix", "2026-10-25", False),
    ("2026_20", "Mexico City Grand Prix", "2026-11-01", False),
    ("2026_21", "Brazilian Grand Prix", "2026-11-08", False),
    ("2026_22", "Las Vegas Grand Prix", "2026-11-22", False),
    ("2026_23", "Qatar Grand Prix", "2026-11-29", False),
    ("2026_24", "Abu Dhabi Grand Prix", "2026-12-06", False),
]

# Results mappings for completed races: (grid, position, points, status)
RESULTS = {
    "2026_1": {
        "RUS": (1, 1, 25.0, "Finished"),
        "ANT": (2, 2, 18.0, "Finished"),
        "LEC": (4, 3, 15.0, "Finished"),
        "HAM": (7, 4, 12.0, "Finished"),
        "NOR": (6, 5, 10.0, "Finished"),
        "VER": (20, 6, 8.0, "Finished"),
        "BEA": (11, 7, 6.0, "Finished"),
        "LIN": (9, 8, 4.0, "Finished"),
        "BOR": (10, 9, 2.0, "Finished"),
        "GAS": (12, 10, 1.0, "Finished"),
        "OCO": (13, 11, 0.0, "Finished"),
        "ALB": (14, 12, 0.0, "Finished"),
        "LAW": (8, 13, 0.0, "Finished"),
        "COL": (15, 14, 0.0, "Finished"),
        "SAI": (16, 15, 0.0, "Finished"),
        "PER": (17, 16, 0.0, "Finished"),
        "BOT": (18, 17, 0.0, "Finished"),
        "PIA": (5, 18, 0.0, "Retired"),
        "STR": (19, 19, 0.0, "Retired"),
        "ALO": (21, 20, 0.0, "Retired"),
        "HAD": (3, 21, 0.0, "Retired"),
        "HUL": (22, 22, 0.0, "Retired"),
    },
    "2026_2": {
        "ANT": (1, 1, 25.0, "Finished"),
        "RUS": (2, 2, 18.0, "Finished"),
        "HAM": (3, 3, 15.0, "Finished"),
        "LEC": (4, 4, 12.0, "Finished"),
        "VER": (8, 5, 10.0, "Finished"),
        "HAD": (9, 6, 8.0, "Finished"),
        "BEA": (10, 7, 6.0, "Finished"),
        "GAS": (7, 8, 4.0, "Finished"),
        "ALB": (18, 9, 2.0, "Finished"),
        "SAI": (11, 10, 1.0, "Finished"),
        "OCO": (12, 11, 0.0, "Finished"),
        "LAW": (13, 12, 0.0, "Finished"),
        "COL": (14, 13, 0.0, "Finished"),
        "ALO": (15, 14, 0.0, "Finished"),
        "STR": (16, 15, 0.0, "Finished"),
        "HUL": (17, 16, 0.0, "Finished"),
        "BOR": (19, 17, 0.0, "Finished"),
        "PER": (20, 18, 0.0, "Finished"),
        "PIA": (5, 19, 0.0, "Retired"),
        "NOR": (6, 20, 0.0, "Retired"),
        "LIN": (21, 21, 0.0, "Retired"),
        "BOT": (22, 22, 0.0, "Retired"),
    },
    "2026_3": {
        "ANT": (1, 1, 25.0, "Finished"),
        "PIA": (3, 2, 18.0, "Finished"),
        "LEC": (4, 3, 15.0, "Finished"),
        "RUS": (2, 4, 12.0, "Finished"),
        "NOR": (5, 5, 10.0, "Finished"),
        "HAM": (6, 6, 8.0, "Finished"),
        "GAS": (7, 7, 6.0, "Finished"),
        "VER": (11, 8, 4.0, "Finished"),
        "LAW": (12, 9, 2.0, "Finished"),
        "OCO": (13, 10, 1.0, "Finished"),
        "HAD": (8, 11, 0.0, "Finished"),
        "BOR": (9, 12, 0.0, "Finished"),
        "LIN": (10, 13, 0.0, "Finished"),
        "ALB": (14, 14, 0.0, "Finished"),
        "SAI": (15, 15, 0.0, "Finished"),
        "COL": (16, 16, 0.0, "Finished"),
        "ALO": (17, 17, 0.0, "Finished"),
        "STR": (18, 18, 0.0, "Finished"),
        "HUL": (19, 19, 0.0, "Finished"),
        "PER": (20, 20, 0.0, "Finished"),
        "BEA": (21, 21, 0.0, "Retired"),
        "BOT": (22, 22, 0.0, "Retired"),
    },
    "2026_6": {
        "ANT": (1, 1, 25.0, "Finished"),
        "NOR": (4, 2, 18.0, "Finished"),
        "PIA": (7, 3, 15.0, "Finished"),
        "RUS": (5, 4, 12.0, "Finished"),
        "VER": (2, 5, 10.0, "Finished"),
        "HAM": (6, 6, 8.0, "Finished"),
        "COL": (8, 7, 6.0, "Finished"),
        "LEC": (3, 8, 4.0, "Finished"),
        "SAI": (13, 9, 2.0, "Finished"),
        "ALB": (15, 10, 1.0, "Finished"),
        "BEA": (12, 11, 0.0, "Finished"),
        "BOR": (14, 12, 0.0, "Finished"),
        "OCO": (16, 13, 0.0, "Finished"),
        "LIN": (18, 14, 0.0, "Finished"),
        "ALO": (17, 15, 0.0, "Finished"),
        "PER": (20, 16, 0.0, "Finished"),
        "STR": (19, 17, 0.0, "Finished"),
        "BOT": (21, 18, 0.0, "Finished"),
        "GAS": (9, 19, 0.0, "Retired"),
        "HUL": (10, 20, 0.0, "Retired"),
        "LAW": (11, 21, 0.0, "Retired"),
        "HAD": (22, 22, 0.0, "Retired"),
    },
    "2026_7": {
        "RUS": (1, None, None, None),
        "ANT": (2, None, None, None),
        "NOR": (3, None, None, None),
        "PIA": (4, None, None, None),
        "HAM": (5, None, None, None),
        "VER": (6, None, None, None),
        "HAD": (7, None, None, None),
        "LEC": (8, None, None, None),
        "LIN": (9, None, None, None),
        "COL": (10, None, None, None),
        "HUL": (11, None, None, None),
        "LAW": (12, None, None, None),
        "BOR": (13, None, None, None),
        "GAS": (14, None, None, None),
        "SAI": (15, None, None, None),
        "BEA": (16, None, None, None),
        "OCO": (17, None, None, None),
        "ALB": (18, None, None, None),
        "ALO": (19, None, None, None),
        "PER": (20, None, None, None),
        "STR": (21, None, None, None),
        "BOT": (22, None, None, None),
    }
}


def compute_championship_standings():
    """
    Compute 2026 championship standings from completed race results.
    Returns a dict of {driver: total_points} sorted descending.
    """
    points_map = {}
    for race_id, race_name, date, is_completed in RACES:
        if not is_completed:
            continue
        for driver, team in DRIVERS_TEAMS:
            _, _, pts, _ = RESULTS[race_id][driver]
            points_map[driver] = points_map.get(driver, 0.0) + pts
    return points_map


def main():
    # Compute standings to use for upcoming race grids
    points_map = compute_championship_standings()
    # Sort drivers by points (descending), then alphabetically for ties
    standings_order = sorted(
        points_map.items(),
        key=lambda x: (-x[1], x[0])
    )
    standings_grid = {driver: idx + 1 for idx, (driver, _) in enumerate(standings_order)}

    print("Championship standings (used for upcoming race grids):")
    for driver, pts in standings_order:
        print(f"  P{standings_grid[driver]:2d}  {driver:4s}  {pts:5.1f} pts")
    print()

    rows = []
    for race_id, race_name, date, is_completed in RACES:
        if is_completed:
            # Load exact results
            race_results = RESULTS[race_id]
            for driver, team in DRIVERS_TEAMS:
                grid, pos, points, status = race_results[driver]
                rows.append([
                    race_id,
                    2026,
                    race_name,
                    date,
                    driver,
                    team,
                    float(grid),
                    float(pos),
                    float(points),
                    status
                ])
        elif race_id == "2026_7":
            # Canada GP has known grid, but empty results
            race_results = RESULTS[race_id]
            for driver, team in DRIVERS_TEAMS:
                grid, _, _, _ = race_results[driver]
                rows.append([
                    race_id,
                    2026,
                    race_name,
                    date,
                    driver,
                    team,
                    float(grid),
                    "",  # position
                    "",  # points
                    ""   # status
                ])
        else:
            # Upcoming races: use championship standings for grid order
            for driver, team in DRIVERS_TEAMS:
                grid = standings_grid.get(driver, 22)
                rows.append([
                    race_id,
                    2026,
                    race_name,
                    date,
                    driver,
                    team,
                    float(grid),
                    "",  # position
                    "",  # points
                    ""   # status
                ])

    with open("f1_2026.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["race_id", "season", "race", "date", "driver", "team", "grid", "position", "points", "status"])
        writer.writerows(rows)

    print("f1_2026.csv created successfully with 22 rows per race!")


if __name__ == "__main__":
    main()
