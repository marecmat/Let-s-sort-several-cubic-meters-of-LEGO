import sys
import json
import time
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).parent.parent / "data"))
from config_api import API_KEY
from config import SETS_FILE, DATABASE_FILE, BASE_URL

HEADERS = {"Authorization": f"key {API_KEY}"}

def load_set_ids():
    with open(SETS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def load_database():
    if Path(DATABASE_FILE).exists():
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)
    return {"sets": {}}

def save_database(database):
    with open(DATABASE_FILE, "w") as f:
        json.dump(database, f, indent=2)

def get_set_parts(set_id):
    url = f"{BASE_URL}/sets/{set_id}-1/parts/"
    parts = []

    while url:
        response = requests.get(url, headers=HEADERS)
        # Rebrickable rate limit
        if response.status_code == 429:
            try:
                wait = response.json()["detail"]
                print(f"\nRate limited: {wait}")
            except Exception:
                print("\nRate limited. Waiting 10 seconds...")
                wait = 10

            time.sleep(10)
            continue

        if response.status_code != 200:
            print(f"\nERROR {response.status_code}: {response.text}")
            return None
        
        data = response.json()
        parts.extend(data["results"])
        url = data["next"]
        # Don't hammer the API.
        if url:
            time.sleep(1)
    return parts

def get_single_set_info(set_id):
    url = f"{BASE_URL}/sets/{set_id}-1/"

    while True:
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 429:
            print("Rate limited, waiting 10 seconds...")
            time.sleep(10)
            continue

        if response.status_code != 200:
            print(
                f"ERROR {response.status_code} "
                f"for set {set_id}: {response.text}"
            )
            return None

        return response.json()


def get_set_infos():
    with open(DATABASE_FILE, "r") as f:
        database = json.load(f)

    sets = database["sets"]

    for i, (set_id, set_data) in enumerate(sets.items(), 1):

        if "name" in set_data:
            print(f"[{i}/{len(sets)}] {set_id} already has a name")
            continue

        print(f"[{i}/{len(sets)}] Getting info for {set_id}...", end=" ")

        info = get_single_set_info(set_id)

        if info is None:
            print("FAILED")
            continue

        set_data["name"] = info["name"]
        set_data["year"] = info["year"]
        set_data["theme_id"] = info["theme_id"]

        with open(DATABASE_FILE, "w") as f:
            json.dump(database, f, indent=2)

        print(f"{info['name']}")

        time.sleep(1)

    print("Done.")


def main():
    set_ids = load_set_ids()
    database = load_database()

    print(f"Found {len(set_ids)} sets.")
    print(f"Already downloaded: {len(database['sets'])}")
    print()

    for i, set_id in enumerate(set_ids, 1):
        if set_id in database["sets"]:
            print(f"[{i}/{len(set_ids)}] {set_id} already downloaded")
            continue

        print(f"[{i}/{len(set_ids)}] Downloading {set_id}...", end=" ")
        parts = get_set_parts(set_id)

        if parts is None:
            print("FAILED")
            continue

        total_pieces = sum(part["quantity"] for part in parts)
        database["sets"][set_id] = {"parts": parts}
        save_database(database)
        print(
            f"OK "
            f"({len(parts)} part types, "
            f"{total_pieces} pieces)"
        )
        # Rate limit between sets.
        time.sleep(1)
    print(
        f"Done. "
        f"{len(database['sets'])}/{len(set_ids)} sets downloaded."
    )
    print(f"Database: {DATABASE_FILE}")

if __name__ == "__main__":
    main()
    get_set_infos()