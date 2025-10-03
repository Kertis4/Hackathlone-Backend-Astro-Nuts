import requests
import os
from dotenv import load_dotenv
import json 


load_dotenv()
API_KEY = os.getenv("API_KEY")

url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date=2025-10-01&end_date=2025-10-07&api_key={API_KEY}"

#gets near earth orbit astroids from the date below
date = "2025-10-03"
response = requests.get(url)
ASTEROID_COUNT = 2
if response.status_code == 200:
    data = response.json()
    asteroids = data["near_earth_objects"][date]

    # Print first 2 asteroids only
    for asteroid in asteroids[:ASTEROID_COUNT]:
        print(json.dumps(asteroid, indent=2))
else:
    print("Error:", response.status_code)