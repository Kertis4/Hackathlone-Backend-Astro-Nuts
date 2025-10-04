# main.py
import os
from datetime import date as Date
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests

load_dotenv()
API_KEY = os.getenv("API_KEY")  # put API_KEY=xxxx in .env

app = FastAPI(title="NASA NEO Data Normalizer")

# (Optional) allow your browser/frontend to call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_asteroid(a: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "hazardous": a.get("is_potentially_hazardous_asteroid"),
        "absolute_magnitude_h": a.get("absolute_magnitude_h"),
        "close_approach_data": a.get("close_approach_data", []),
        "nasa_jpl_url": a.get("nasa_jpl_url"),
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/asteroids")
def get_asteroids(
    start_date: Date = Query(..., description="YYYY-MM-DD"),
    end_date:   Date = Query(..., description="YYYY-MM-DD"),
) -> List[Dict[str, Any]]:
    if not API_KEY:
        raise HTTPException(500, "API_KEY missing. Add API_KEY=... to your .env")

    if end_date < start_date:
        raise HTTPException(400, "end_date must be >= start_date")

    # NASA feed allows max 7 days inclusive
    if (end_date - start_date).days + 1 > 7:
        raise HTTPException(400, "Range too large. Use at most 7 days inclusive.")

    url = "https://api.nasa.gov/neo/rest/v1/feed"
    try:
        r = requests.get(
            url,
            params={"start_date": str(start_date), "end_date": str(end_date), "api_key": API_KEY},
            timeout=30,
            headers={"User-Agent": "neo-client/1.0"}  # harmless; avoids odd blocks
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"NASA API request failed: {e}")

    if r.status_code != 200:
        # show NASA's actual message to distinguish "invalid key" vs "rate limit"
        try:
            j = r.json()
            msg = j.get("error_message") or j.get("message") or j
        except Exception:
            msg = r.text[:500]
        raise HTTPException(r.status_code, f"NASA API error: {msg}")

    data = r.json()
    days = data.get("near_earth_objects") or {}
    out: List[Dict[str, Any]] = []
    for _, items in days.items():
        out.extend(items)
    return [normalize_asteroid(a) for a in out]

# Optional: run with `python main.py` (handy on Windows/Task Scheduler)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",  # keep localhost for safety
        port=8080,
        reload=False       # True for dev hot-reload
    )
