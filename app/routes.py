from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.schemas import SimulationRequest, SimulationResponse, HealthResponse
from app.services.simulator import SimulationService
from app.config import settings
from datetime import datetime
import os

router = APIRouter()
simulator_service = SimulationService()

@router.post("/simulations", response_model=SimulationResponse, status_code=201)
async def create_simulation(request: SimulationRequest):
    """
    Create and run a new solar panel power simulation
    
    propagation_method: 'circular' or 'tle'
    altitude_km: Orbit altitude (circular method only)
    inclination_deg: Orbit inclination (circular method only)
    tle_line1/tle_line2: TLE data (TLE method only)
    panel_area_m2: Solar panel area
    panel_efficiency: Panel efficiency (0.29 = 29%)
    duration_hours: How long to simulate
    """
    result = simulator_service.run_simulation(request)
    
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.message)
    
    return result

@router.get("/outputs/{filename}")
async def get_output_file(filename: str):
    """
    Download generated output file (plot or CSV)
    """
    filepath = os.path.join(settings.OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    if filename.endswith('.png'):
        media_type = "image/png"
    elif filename.endswith('.csv'):
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"    

    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename
    )

@router.get("/simulations/examples")
async def get_examples():
    return {
        "circular_orbit_iss_like": {
            "propagation_method": "circular",
            "altitude_km": 420,
            "inclination_deg": 51.6,
            "panel_area_m2": 15,
            "panel_efficiency": 0.29,
            "start_time": "2024-01-15T00:00:00",
            "duration_hours": 3,
            "time_step_seconds": 60
        },
        "circular_orbit_polar": {
            "propagation_method": "circular",
            "altitude_km": 800,
            "inclination_deg": 90,
            "panel_area_m2": 20,
            "panel_efficiency": 0.30,
            "start_time": "2024-01-15T00:00:00",
            "duration_hours": 6,
            "time_step_seconds": 120
        },
        "tle_orbit_iss": {
            "propagation_method": "tle",
            "tle_line1": "1 25544U 98067A   24015.50000000  .00012345  00000-0  12345-3 0  9992",
            "tle_line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391123456",
            "panel_area_m2": 15,
            "panel_efficiency": 0.29,
            "start_time": "2024-01-15T00:00:00",
            "duration_hours": 3,
            "time_step_seconds": 60
        }
    }
