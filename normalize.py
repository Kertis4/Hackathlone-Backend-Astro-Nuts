import json

def extract_asteroids_from_feed(feed_response):
    """
    Extract and flatten all asteroid data from the /feed endpoint response.
    Returns a list of asteroid dicts.
    """
    all_asteroids = []
    near_earth_objects = feed_response.get("near_earth_objects", {})
    
    for date in near_earth_objects:
        all_asteroids.extend(near_earth_objects[date])
    
    return all_asteroids


def normalize_asteroid_data(raw_data):
    """
    Normalize a single asteroid entry from NASA's NEO API into a flat dictionary.
    """
    diameter = raw_data["estimated_diameter"]
    normalized = {
        "id": raw_data.get("id"),
        "name": raw_data.get("name"),
        "nasa_jpl_url": raw_data.get("nasa_jpl_url"),
        "absolute_magnitude_h": raw_data.get("absolute_magnitude_h"),

        # Estimated diameters in various units
        "estimated_diameter_km_min": diameter["kilometers"]["estimated_diameter_min"],
        "estimated_diameter_km_max": diameter["kilometers"]["estimated_diameter_max"],
        "estimated_diameter_m_min": diameter["meters"]["estimated_diameter_min"],
        "estimated_diameter_m_max": diameter["meters"]["estimated_diameter_max"],
        "estimated_diameter_mi_min": diameter["miles"]["estimated_diameter_min"],
        "estimated_diameter_mi_max": diameter["miles"]["estimated_diameter_max"],
        "estimated_diameter_ft_min": diameter["feet"]["estimated_diameter_min"],
        "estimated_diameter_ft_max": diameter["feet"]["estimated_diameter_max"],

        "is_potentially_hazardous_asteroid": raw_data.get("is_potentially_hazardous_asteroid"),
        "is_sentry_object": raw_data.get("is_sentry_object")
    }

    # Normalize first close approach data if available
    if raw_data.get("close_approach_data"):
        approach = raw_data["close_approach_data"][0]
        velocity = approach["relative_velocity"]
        distance = approach["miss_distance"]

        normalized.update({
            "close_approach_date": approach.get("close_approach_date"),
            "close_approach_date_full": approach.get("close_approach_date_full"),
            "epoch_date_close_approach": approach.get("epoch_date_close_approach"),
            "relative_velocity_km_s": float(velocity["kilometers_per_second"]),
            "relative_velocity_km_h": float(velocity["kilometers_per_hour"]),
            "relative_velocity_mph": float(velocity["miles_per_hour"]),
            "miss_distance_au": float(distance["astronomical"]),
            "miss_distance_lunar": float(distance["lunar"]),
            "miss_distance_km": float(distance["kilometers"]),
            "miss_distance_mi": float(distance["miles"]),
            "orbiting_body": approach.get("orbiting_body")
        })

    return normalized


def normalize_multiple_asteroids(data_list):
    """
    Normalize a list of asteroid objects from NASA's NEO API.

    Parameters:
        data_list (list): List of raw asteroid JSON objects.

    Returns:
        list: List of normalized asteroid dictionaries.
    """
    return [normalize_asteroid_data(asteroid) for asteroid in data_list]


# ---------- Sample Data ---------- #
sample_asteroid_data = {
    "links": {
        "self": "http://api.nasa.gov/neo/rest/v1/neo/2465633?api_key=DEMO_KEY"
    },
    "id": "2465633",
    "neo_reference_id": "2465633",
    "name": "465633 (2009 JR5)",
    "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2465633",
    "absolute_magnitude_h": 20.44,
    "estimated_diameter": {
        "kilometers": {
            "estimated_diameter_min": 0.2170475943,
            "estimated_diameter_max": 0.4853331752
        },
        "meters": {
            "estimated_diameter_min": 217.0475943071,
            "estimated_diameter_max": 485.3331752235
        },
        "miles": {
            "estimated_diameter_min": 0.1348670807,
            "estimated_diameter_max": 0.3015719604
        },
        "feet": {
            "estimated_diameter_min": 712.0984293066,
            "estimated_diameter_max": 1592.3004946003
        }
    },
    "is_potentially_hazardous_asteroid": True,
    "close_approach_data": [
        {
            "close_approach_date": "2015-09-08",
            "close_approach_date_full": "2015-Sep-08 20:28",
            "epoch_date_close_approach": 1441744080000,
            "relative_velocity": {
                "kilometers_per_second": "18.1279360862",
                "kilometers_per_hour": "65260.5699103704",
                "miles_per_hour": "40550.3802312521"
            },
            "miss_distance": {
                "astronomical": "0.3027469457",
                "lunar": "117.7685618773",
                "kilometers": "45290298.225725659",
                "miles": "28142086.3515817342"
            },
            "orbiting_body": "Earth"
        }
    ],
    "is_sentry_object": False
}

# ---------- Run & Output ---------- #
asteroid_batch = [sample_asteroid_data, sample_asteroid_data]  # Simulating a list of multiple entries
normalized_batch = normalize_multiple_asteroids(asteroid_batch)

print(json.dumps(normalized_batch, indent=2))

# Example: Suppose you got this from the real /feed endpoint (mocked here)
fake_feed_response = {
    "near_earth_objects": {
        "2025-10-01": [sample_asteroid_data],
        "2025-10-02": [sample_asteroid_data, sample_asteroid_data]
    }
}

# Step 1: Extract asteroid list
asteroid_batch = extract_asteroids_from_feed(fake_feed_response)

# Step 2: Normalize
normalized_batch = normalize_multiple_asteroids(asteroid_batch)

# Step 3: Output
print(json.dumps(normalized_batch, indent=2))
