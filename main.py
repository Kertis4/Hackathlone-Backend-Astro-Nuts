import os
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
import json 
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# PYDANTIC MODELS FOR REQUEST VALIDATION
# ============================================================================
class ReportRequest(BaseModel):
    asteroidIds: List[str]

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
# AI ANALYSIS ENDPOINTS - NEW: HTML REPORT GENERATION
# ============================================================================

@app.post("/ai/report")
async def generate_html_report(request: ReportRequest):
    """
    Generate HTML report for selected asteroids
    Receives: { "asteroidIds": ["id1", "id2", ...] }
    Returns: Complete HTML document with embedded CSS
    """
    try:
        # Get asteroid data from database
        asteroids_data = []
        for asteroid_id in request.asteroidIds:
            result = normalize_asteroids(asteroid_id)
            if result:
                try:
                    asteroids_data.append(json.loads(result))
                except:
                    # If result is already a dict
                    asteroids_data.append(result)
        
        if not asteroids_data:
            raise HTTPException(
                status_code=404,
                detail="No asteroids found for provided IDs"
            )
        
        # Debug: Print first asteroid structure to see what we have
        print("First asteroid data structure:")
        print(json.dumps(asteroids_data[0], indent=2))
        
        # Prepare asteroid summary - DEFENSIVE VERSION
        asteroid_summary_list = []
        for a in asteroids_data:
            try:
                # Try to extract data safely with fallbacks
                name = a.get('name', 'Unknown')
                
                # Try different possible structures for diameter
                diameter = None
                if 'estimated_diameter' in a:
                    if 'kilometers' in a['estimated_diameter']:
                        diameter = a['estimated_diameter']['kilometers'].get('estimated_diameter_max', 0)
                    elif 'estimated_diameter_km_max' in a['estimated_diameter']:
                        diameter = a['estimated_diameter'].get('estimated_diameter_km_max', 0)
                elif 'estimated_diameter_km_max' in a:
                    diameter = a.get('estimated_diameter_km_max', 0)
                
                # Try different possible structures for velocity
                velocity = None
                if 'close_approach_data' in a and len(a['close_approach_data']) > 0:
                    if 'relative_velocity' in a['close_approach_data'][0]:
                        velocity = a['close_approach_data'][0]['relative_velocity'].get('kilometers_per_second', 0)
                elif 'relative_velocity_km_s' in a:
                    velocity = a.get('relative_velocity_km_s', 0)
                
                # Try different possible structures for distance
                distance = None
                if 'close_approach_data' in a and len(a['close_approach_data']) > 0:
                    if 'miss_distance' in a['close_approach_data'][0]:
                        distance = a['close_approach_data'][0]['miss_distance'].get('astronomical', 0)
                elif 'miss_distance_au' in a:
                    distance = a.get('miss_distance_au', 0)
                
                # Get hazardous status
                is_hazardous = a.get('is_potentially_hazardous_asteroid', False)
                
                # Get approach date
                approach_date = None
                if 'close_approach_data' in a and len(a['close_approach_data']) > 0:
                    approach_date = a['close_approach_data'][0].get('close_approach_date_full', 'Unknown')
                elif 'close_approach_date_full' in a:
                    approach_date = a.get('close_approach_date_full', 'Unknown')
                
                # Build summary string
                summary_parts = [f"- {name}"]
                if diameter:
                    summary_parts.append(f"{diameter:.2f} km diameter")
                if velocity:
                    summary_parts.append(f"{velocity:.2f} km/s velocity")
                if distance:
                    summary_parts.append(f"Miss distance: {distance:.4f} AU")
                summary_parts.append(f"Potentially hazardous: {is_hazardous}")
                if approach_date:
                    summary_parts.append(f"Close approach: {approach_date}")
                
                asteroid_summary_list.append(", ".join(summary_parts))
                
            except Exception as e:
                print(f"Error processing asteroid: {e}")
                # Fallback: just dump the whole object as JSON
                asteroid_summary_list.append(f"- {json.dumps(a, indent=2)}")
        
        asteroid_summary = "\n".join(asteroid_summary_list)
        
        print("Asteroid summary being sent to AI:")
        print(asteroid_summary)
        
        # Call OpenAI to generate HTML report
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert asteroid impact analyst. Generate a professional, 
                    clean HTML report with subtle styling. Use minimal colors - primarily white/light 
                    backgrounds with dark text for readability. Apply accent colors sparingly only for 
                    headers, borders, and highlights. The design should be modern, clean, and 
                    professional - think scientific journal or government report aesthetic."""
                },
                {
                    "role": "user",
                    "content": f"""Generate a complete HTML document for an asteroid impact assessment report.

**OVERALL GUIDELINES**
- Try avoid such as, use specifics
- Specific information for preventing specific asteroid sizes                  



**STYLING REQUIREMENTS:**
- Primary background: White (#FFFFFF) or very light gray (#F8F9FA)
- Primary text: Dark gray or black (#1A1A1A or #2D3748)
- Accent color (use sparingly for headers/borders): Teal (#1BA098)
- Secondary accent (use minimally): Tan/beige (#DEB992)
- Dark accent (for contrast): Deep blue (#051622)

**DESIGN GUIDELINES:**
- Use clean, professional typography (system fonts: -apple-system, sans-serif)
- Subtle borders and shadows only
- White/light card backgrounds with thin colored borders
- Colored headers but keep body text black/dark gray
- Tables with light gray zebra striping
- Risk indicators can use standard red/orange/yellow/green
- NO dark backgrounds - keep it light and readable
- Minimal use of gradients - prefer solid colors
- Professional spacing and padding
- make sure the text for the header is not the same as the font for the title

**CONTENT STRUCTURE:**
1. Executive Summary (with key statistics)
2. Individual Asteroid Analysis (one section per asteroid)
3. Risk Assessment Matrix
4. Impact Scenarios (if applicable)
4. Mitigation Strategies (use specific and best practices)
5. Recommendations

**Asteroids to analyze:**
{asteroid_summary}

Generate a complete HTML document starting with <!DOCTYPE html> and including all necessary CSS in a <style> tag."""
                }
            ],
            max_tokens=4000,
            temperature=0.7
        )
        
        html_report = response.choices[0].message.content
        
        # Return HTML directly
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_report)
        
    except Exception as e:
        # Enhanced error reporting
        import traceback
        error_detail = f"Failed to generate report: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Print to console for debugging
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


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
                "/ai/report (POST)",
                "/ai/generalSummary/{ids}",
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
