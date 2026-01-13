import feedparser
import time
import os
import json
import argparse
from pymongo import MongoClient

# RSS Feed Ingestion Module. Configurable crawler that retrieves news data from defined RSS endpoints, 
# archives raw payloads locally, and performs deduplicated insertion of news entries into the MongoDB database. 
# Supports both single-execution and scheduled periodic extraction modes.

# Port for MongoDB
MONGO_PORT = 27017

# Function for recursive data sanitization.
def clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

# Credential management utility.
def load_credentials(path='login.txt'):
    creds = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                creds[key.strip()] = value.strip()
    return creds.get('user'), creds.get('password')

# Iterates through configured RSS endpoints, parses feed data, 
# archives raw JSON payloads to local storage, and performs content-based deduplication
def run_task():
    rss_file = 'rss_newspaper.txt'
    root_folder = 'rss_saved'
    os.makedirs(root_folder, exist_ok=True)

    # Read credentials
    user, password = load_credentials()
    if not user or not password:
        print("Error: Could not read MongoDB credentials.")
        return

    client = MongoClient(f"mongodb://{user}:{password}@noRelational_db:{MONGO_PORT}/")
    db = client['newspapers_db']

    with open(rss_file, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file if line.strip()]

    for line in lines:
        name, url = line.split(':', 1)
        name = name.strip().replace(' ', '_')
        url = url.strip()

        print(f"\n========== {name} ==========")

        newspaper_folder = os.path.join(root_folder, name)
        os.makedirs(newspaper_folder, exist_ok=True)

        epoch_time = int(time.time())
        feed = feedparser.parse(url)

        try:
            rss_data_dict = clean_for_json(dict(feed))
            filename = f"{name}_{epoch_time}.json"
            full_path = os.path.join(newspaper_folder, filename)

            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(rss_data_dict, f, ensure_ascii=False, indent=4)

            print(f"RSS from {name} saved at: {full_path}")
        except Exception as e:
            print(f"Error saving JSON for {name}: {e}")

        collection = db[name]
        entries = []
        for entry in feed.entries:
            headline = entry.get('title', 'No title')
            description = entry.get('description', entry.get('summary', 'No description'))

            if collection.count_documents({'headline': headline, 'description': description}, limit=1) == 0:
                new_entry = {
                    'headline': headline,
                    'description': description,
                    'date_stored': epoch_time
                }
                entries.append(new_entry)

        if entries:
            collection.insert_many(entries)
            print(f"Inserted {len(entries)} new entries into the '{name}' collection in MongoDB.")
        else:
            print(f"No new entries to insert for {name}.")

# === CLI Arguments ===
parser = argparse.ArgumentParser(description="Runs the script once or periodically.")
parser.add_argument("--duration", help="Total duration in minutes (or '*' for infinite).")
parser.add_argument("--interval", type=int, help="Interval between runs in minutes.")
args = parser.parse_args()

# === Execute according to mode ===
if args.duration is None or args.interval is None:
    run_task()
else:
    interval_sec = args.interval * 60

    if args.duration == "*":
        print("\nRunning in infinite mode.")
        while True:
            print(f"\n Executing at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            run_task()
            time.sleep(interval_sec)
    else:
        try:
            total_duration_sec = int(args.duration) * 60
            start_time = time.time()
            end_time = start_time + total_duration_sec

            while time.time() < end_time:
                print(f"\n Executing at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                run_task()
                remaining_time = end_time - time.time()
                if remaining_time > interval_sec:
                    time.sleep(interval_sec)
                else:
                    break
        except ValueError:
            print("Error: --duration must be an integer or '*'.")