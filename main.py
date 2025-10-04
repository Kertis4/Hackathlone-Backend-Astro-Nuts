import requests
import os
from dotenv import load_dotenv
import json 
from fastapi import FastAPI, HTTPException
import uvicorn
from normalize import normalize_multiple_asteroids

from typing import List, Dict, Any    

load_dotenv()
API_KEY = os.getenv("API_KEY")
url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date=2025-10-01&end_date=2025-10-07&api_key={API_KEY}"
app = FastAPI(title="NASA NEO Data Normalizer")
DATE = "2025-10-05"


#gets near earth orbit astroids from the date below

response = requests.get(url)

@app.get("/asteroids/{date}")
def get_json_asteroid(date: str):
  
    ASTEROID_COUNT = 2
    if response.status_code == 200:
        data = response.json()
        asteroids = data["near_earth_objects"][date]

        # Print first 2 asteroids only
        for asteroid in asteroids:
            #print(json.dumps(asteroid, indent=2))
            print(normalize_multiple_asteroids(json.dumps(asteroid, indent=2)))
    else:
        print("Error:", response.status_code)


    




#print(normalize_asteroid(get_json_asteroid(DATE)))
get_json_asteroid(DATE)