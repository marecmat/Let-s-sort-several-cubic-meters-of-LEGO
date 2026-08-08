import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "data"))
from config import DATABASE_FILE

def load_database():
    print(f"Loading database from:\n{DATABASE_FILE}")
    with open(DATABASE_FILE, "r",) as file:
        database = json.load(file)

    print(f"Loaded {len(database['sets'].items())} sets.")
    return database

def find_destinations(database, brickognize_result):
    """
    Find all sets that contain the part identified by Brickognize.

    The database represents the original set inventories.
    Nothing is consumed or modified.
    """

    if "error" in brickognize_result:
        return []

    items = brickognize_result.get("items", [])

    if not items:
        return []

    # Brickognize's best prediction.
    best = items[0]

    part_id = best["id"]
    confidence = best["score"]

    candidates = []

    for set_id, set_data in database["sets"].items():

        for entry in set_data["parts"]:

            # Ignore spare parts.
            if entry.get("is_spare", False):
                continue

            if entry["part"]["part_num"] != part_id:
                continue

            candidates.append({
                "set_id": set_id,
                "set_name": set_data.get(
                    "name",
                    "Unknown set"
                ),
                "part_id": entry["part"]["part_num"],
                "part_name": entry["part"]["name"],
                "color": entry["color"]["name"],
                "quantity": entry["quantity"],
                "confidence": confidence,
            })

    return candidates


def print_destinations(candidates, brickognize_result):
    """
    Print the possible destinations for one brick.
    """

    if not brickognize_result.get("items"):
        print("No brick identified.")
        return

    best = brickognize_result["items"][0]

    print()
    print("=" * 90)

    print(
        f"{best['id']} - "
        f"{best['name']}"
    )

    print(
        f"Brickognize confidence: "
        f"{best['score']:.1%}"
    )

    print("=" * 90)

    if not candidates:

        print()
        print("NO MATCHING SET FOUND")
        print()

        return

    if len(candidates) == 1:

        candidate = candidates[0]

        print()
        print("ONE POSSIBLE SET")
        print()

        print(
            f"  SET:   {candidate['set_id']}-1"
        )

        print(
            f"  NAME:  {candidate['set_name']}"
        )

        print(
            f"  COLOR: {candidate['color']}"
        )

        print(
            f"  QTY:   {candidate['quantity']}"
        )

        print()

        return

    print()
    print(
        f"{len(candidates)} POSSIBLE SETS"
    )
    print()

    print(
        f"{'SET':<10}"
        f"{'COLOR':<25}"
        f"{'QTY':>5}  "
        f"NAME"
    )

    print("-" * 90)

    for candidate in candidates:

        print(
            f"{candidate['set_id']:<10}"
            f"{candidate['color']:<25}"
            f"{candidate['quantity']:>5}  "
            f"{candidate['set_name']}"
        )

    print()

    print(
        "Use the physical color of the brick "
        "to choose the destination."
    )

    print()


def print_batch_results(database, results):
    """
    Print the sorting information for every brick found
    in the batch.
    """

    print()
    print()
    print("#" * 90)
    print(
        f"FOUND {len(results)} BRICKS"
    )
    print("#" * 90)

    for number, result in enumerate(results, 1):

        brick = result["items"][0]

        candidates = find_destinations(
            database,
            result
        )

        print()
        print(
            f"[BRICK {number}] "
            f"{brick['id']} - "
            f"{brick['name']} "
            f"({brick['score']:.1%})"
        )

        if not candidates:

            print(
                "    -> NO MATCHING SET"
            )

        elif len(candidates) == 1:

            candidate = candidates[0]

            print(
                f"    -> SET "
                f"{candidate['set_id']}-1"
            )

            print(
                f"       {candidate['set_name']}"
            )

            print(
                f"       Color: "
                f"{candidate['color']}"
            )

        else:

            print(
                f"    -> {len(candidates)} possible sets:"
            )

            for candidate in candidates:

                print(
                    f"       "
                    f"{candidate['set_id']}-1  "
                    f"{candidate['color']:<20} "
                    f"{candidate['set_name']}"
                )

    print()
    print("#" * 90)
    print()

if __name__ == "__main__":
    database = load_database()
