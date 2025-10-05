import os
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
import json 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # ADD THIS
import uvicorn
from normalize import normalize_asteroids, get_all_asteroid_ids, get_all_asteroids_normalized
import datetime
import sqlite3
import requests


# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPEN_AI_KEY)

# Initialize FastAPI app
app = FastAPI(title="NASA NEO Data Normalizer")

# ============================================================================
# CONFIGURE CORS
# ============================================================================
origins = [
    "http://localhost:5173",      # Vite default
    "http://localhost:3000",      # Create React App default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Date configurations
DATE = datetime.date.today().strftime('%Y-%m-%d')
START_DATE = datetime.date.today().strftime("%Y-%m-%d")
END_DATE = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
URL = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={START_DATE}&end_date={END_DATE}&api_key={API_KEY}"

# Database connection
conn = sqlite3.connect("asteroids.db", check_same_thread=False)
cur = conn.cursor()


# ============================================================================
# ASTEROID DATABASE ENDPOINTS
# ============================================================================

@app.get("/database/asteroids")
def get_asteroids_from_db():
    """
    Get all asteroids from database in normalized format
    Returns: List of all asteroids with complete data
    """
    return get_all_asteroids_normalized()


@app.get("/database/asteroids/ids")
def get_all_ids():
    """
    Get list of all asteroid IDs in database
    Returns: JSON with array of asteroid IDs
    """
    return {"asteroid_ids": get_all_asteroid_ids()}


@app.get("/database/asteroids/{asteroid_id}")
def get_asteroid_by_id(asteroid_id: str):
    """
    Get a single asteroid by ID in normalized format
    Args:
        asteroid_id: The neo_reference_id of the asteroid
    Returns: Complete asteroid data in normalized format
    """
    result = normalize_asteroids(asteroid_id)
    
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Asteroid with ID {asteroid_id} not found"
        )
    
    return json.loads(result)


# ============================================================================
# NASA API ENDPOINT (Legacy - for direct API fetching)
# ============================================================================

@app.get("/asteroids/{date}")
def get_asteroids_from_api(date: str):
    """
    Fetch asteroids directly from NASA API for a specific date
    This endpoint is for testing/comparison with database data
    """
    try:
        response = requests.get(URL)
        
        if response.status_code == 200:
            data = response.json()
            asteroids = data.get("near_earth_objects", {}).get(date, [])
            
            if not asteroids:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No asteroids found for date {date}"
                )
            
            return asteroids
        else:
            raise HTTPException(
                status_code=response.status_code, 
                detail="Error fetching from NASA API"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/ai/generalSummary/{ids}")
def ai_generalSummary(ids):
    asteroids = {}
    """
    Get AI-generated general summary of all asteroids
    Uses GPT-4 to analyze asteroid data and provide policy recommendations
    """
    # get data for asteroids provided from database
    for id in ids:
        asteroids[id] = normalize_asteroids(id)
   
    if not asteroids:
        raise HTTPException(
            status_code=404, 
            detail="No asteroids found in database"
        )
    
    # Prepare data for AI (limit to recent/important asteroids if too many)
    #asteroid_summary = json.dumps(asteroids[:1000], indent=2)  # Limit to 50 for token limits
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a professional astronomer/physicist explaining to policy makers. Discuss asteroid impact scenarios, predict consequences, and evaluate potential mitigation strategies. Avoid jargon where applicable."
            }, 
            {
                "role": "user",
                "content": f"Analyze these near-Earth asteroids and provide a summary:\n\n{asteroids}"
            }
        ],
        max_tokens=1000,
        temperature=1
    )
    print(response.choices[0].message.content)
    return {
        "summary": response.choices[0].message.content,
        #"asteroids_analyzed": len(asteroids[:50]),
        #"total_asteroids": len(asteroids)
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
def root():
    """
    Root endpoint - API health check
    """
    return {
        "status": "online",
        "api_name": "NASA NEO Data Normalizer",
        "endpoints": {
            "database": [
                "/database/asteroids",
                "/database/asteroids/ids",
                "/database/asteroids/{asteroid_id}"
            ],
            "ai_analysis": [
                "/ai/generalSummary",
                "/ai/individualReport/{asteroid_id}"
            ],
            "nasa_api": [
                "/asteroids/{date}"
            ]
        }
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True  # Enable hot reload for development
    )

#print(ai_generalSummary([3427459, 3716631]))