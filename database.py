import sqlite3
import requests
import datetime

# 🔑 Your NASA API key
API_KEY = "zXWmLUFqfMSNBIfXSfe0JS025dKYVXD81Dp9oEad"

# Example: Get asteroids between these dates
START_DATE = datetime.date.today().strftime("%Y-%m-%d")
END_DATE = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

URL = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={START_DATE}&end_date={END_DATE}&api_key={API_KEY}"

# Fetch data from NASA API
response = requests.get(URL)
data = response.json()

# --- DEBUG: show response in case of error ---
if "near_earth_objects" not in data:
    print("❌ Error from NASA API:", data)
    exit()

# Connect to SQLite (creates file if not exists)
conn = sqlite3.connect("asteroids.db")
cursor = conn.cursor()

# Create main asteroids table
cursor.execute("""
CREATE TABLE IF NOT EXISTS asteroids (
    id TEXT PRIMARY KEY,
    neo_reference_id TEXT,
    name TEXT,
    nasa_jpl_url TEXT,
    absolute_magnitude_h REAL,
    is_potentially_hazardous INTEGER,
    is_sentry_object INTEGER
);
""")

# Create asteroid diameters table
cursor.execute("""
CREATE TABLE IF NOT EXISTS asteroid_diameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asteroid_id TEXT,
    unit TEXT,
    diameter_min REAL,
    diameter_max REAL,
    FOREIGN KEY (asteroid_id) REFERENCES asteroids(id)
);
""")

# Create close approaches table
cursor.execute("""
CREATE TABLE IF NOT EXISTS close_approaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asteroid_id TEXT,
    close_approach_date TEXT,
    close_approach_date_full TEXT,
    epoch_date_close_approach INTEGER,
    velocity_km_s REAL,
    velocity_km_h REAL,
    velocity_mi_h REAL,
    miss_distance_astronomical REAL,
    miss_distance_lunar REAL,
    miss_distance_km REAL,
    miss_distance_miles REAL,
    orbiting_body TEXT,
    FOREIGN KEY (asteroid_id) REFERENCES asteroids(id)
);
""")

# Process each asteroid from the feed
for date, asteroids in data["near_earth_objects"].items():
    for asteroid in asteroids:
        # Insert asteroid main info
        cursor.execute("""
        INSERT OR REPLACE INTO asteroids
        (id, neo_reference_id, name, nasa_jpl_url, absolute_magnitude_h, is_potentially_hazardous, is_sentry_object)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            asteroid["id"],
            asteroid["neo_reference_id"],
            asteroid["name"],
            asteroid["nasa_jpl_url"],
            asteroid["absolute_magnitude_h"],
            int(asteroid["is_potentially_hazardous_asteroid"]),
            int(asteroid.get("is_sentry_object", False))
        ))

        # Insert diameter data
        for unit, values in asteroid["estimated_diameter"].items():
            cursor.execute("""
            INSERT INTO asteroid_diameters
            (asteroid_id, unit, diameter_min, diameter_max)
            VALUES (?, ?, ?, ?)
            """, (
                asteroid["id"],
                unit,
                values["estimated_diameter_min"],
                values["estimated_diameter_max"]
            ))

        # Insert close approach data
        for approach in asteroid["close_approach_data"]:
            cursor.execute("""
            INSERT INTO close_approaches
            (asteroid_id, close_approach_date, close_approach_date_full,
            epoch_date_close_approach, velocity_km_s, velocity_km_h, velocity_mi_h,
            miss_distance_astronomical, miss_distance_lunar, miss_distance_km, miss_distance_miles,
            orbiting_body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asteroid["id"],
                approach["close_approach_date"],
                approach.get("close_approach_date_full"),
                approach.get("epoch_date_close_approach"),
                float(approach["relative_velocity"]["kilometers_per_second"]),
                float(approach["relative_velocity"]["kilometers_per_hour"]),
                float(approach["relative_velocity"]["miles_per_hour"]),
                float(approach["miss_distance"]["astronomical"]),
                float(approach["miss_distance"]["lunar"]),
                float(approach["miss_distance"]["kilometers"]),
                float(approach["miss_distance"]["miles"]),
                approach["orbiting_body"]
            ))

# Commit changes & close
conn.commit()

print("\nInserted asteroids:")
for row in cursor.execute("SELECT id, name, is_potentially_hazardous FROM asteroids LIMIT 10"):
    print(row)

conn.close()
print("\nAll asteroid data inserted successfully 🚀")
