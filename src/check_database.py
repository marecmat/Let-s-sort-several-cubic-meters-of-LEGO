import json
import sys


from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "data"))
from config import DATABASE_FILE


def load_database():
    with open(DATABASE_FILE, "r") as f:
        return json.load(f)


def inspect_set(set_id, set_data):
    parts = set_data["parts"]

    normal_parts = [
        part for part in parts
        if not part.get("is_spare", False)
    ]

    spare_parts = [
        part for part in parts
        if part.get("is_spare", False)
    ]

    total_pieces = sum(
        part["quantity"]
        for part in normal_parts
    )

    set_name = set_data.get("name", "Unknown set")

    print()
    print("=" * 100)
    print(f"SET {set_id}-1 — {set_name}")
    print("=" * 100)
    print(f"Part types : {len(parts)}")
    print(f"Pieces     : {total_pieces}")

    if spare_parts:
        spare_count = sum(
            part["quantity"]
            for part in spare_parts
        )
        print(f"Spare parts: {spare_count}")

    print()

    # Calculate column widths.
    part_width = max(
        len("PART"),
        max(len(str(p["part"]["part_num"])) for p in parts)
    )

    name_width = max(
        len("DESCRIPTION"),
        max(len(p["part"]["name"]) for p in parts)
    )

    color_width = max(
        len("COLOR"),
        max(len(p["color"]["name"]) for p in parts)
    )

    # Don't let absurdly long descriptions destroy the terminal.
    name_width = min(name_width, 55)

    print(
        f"{'PART':<{part_width}}  "
        f"{'DESCRIPTION':<{name_width}}  "
        f"{'COLOR':<{color_width}}  "
        f"{'QUANTITY':>8}"
    )

    print("-" * (
        part_width +
        name_width +
        color_width +
        20
    ))

    # Sort by color, then part number.
    parts = sorted(
        parts,
        key=lambda p: (
            p["color"]["name"],
            p["part"]["part_num"]
        )
    )

    for entry in parts:
        part = entry["part"]
        color = entry["color"]

        part_num = part["part_num"]
        description = part["name"]
        color_name = color["name"]
        quantity = entry["quantity"]

        if len(description) > name_width:
            description = description[:name_width - 3] + "..."

        quantity_text = str(quantity)

        if entry.get("is_spare", False):
            quantity_text += " (spare)"

        print(
            f"{part_num:<{part_width}}  "
            f"{description:<{name_width}}  "
            f"{color_name:<{color_width}}  "
            f"{quantity_text:>8}"
        )

    print()


def print_summary(database):
    sets = database["sets"]

    print(f"Database contains {len(sets)} sets.")
    print()

    total_pieces = 0

    for set_id, set_data in sets.items():
        parts = set_data["parts"]

        pieces = sum(
            part["quantity"]
            for part in parts
            if not part.get("is_spare", False)
        )

        total_pieces += pieces

        name = set_data.get("name", "Unknown set")

        print(
            f"{set_id:<8} "
            f"{pieces:>5} pieces   "
            f"{name}"
        )

    print()
    print(f"Total physical pieces: {total_pieces}")


def main():
    database = load_database()
    sets = database["sets"]

    if len(sys.argv) > 1:
        set_id = sys.argv[1]

        if set_id not in sets:
            print(f"Set {set_id} not found.")
            return

        inspect_set(set_id, sets[set_id])
    else:
        print_summary(database)


if __name__ == "__main__":
    main()