from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.schemas import SimulationRequest, SimulationResponse, SimulationDetailResponse
from app.services.simulator import SimulationService
from app.config import settings
from app.database import get_db
from datetime import datetime
from app.models import Simulation
from sqlalchemy.orm import Session
import os

router = APIRouter()
simulator_service = SimulationService()

@router.post("/simulations", response_model=SimulationResponse, status_code=201)
async def create_simulation(request: SimulationRequest):
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

@router.get("/simulations/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation_by_id(simulation_id: str, db: Session = Depends(get_db)):
    simulation = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation with ID '{simulation_id}' not found")
    
    return SimulationDetailResponse(
        simulation_id=simulation.simulation_id,
        created_at=simulation.created_at.isoformat(),
        status=simulation.status,
        error_message=simulation.error_message,
        propagation_method=simulation.propagation_method,
        altitude_km=simulation.altitude_km,
        inclination_deg=simulation.inclination_deg,
        tle_line1=simulation.tle_line1,
        tle_line2=simulation.tle_line2,
        panel_area_m2=simulation.panel_area_m2,
        panel_efficiency=simulation.panel_efficiency,
        start_time=simulation.start_time,
        duration_hours=simulation.duration_hours,
        time_step_seconds=simulation.time_step_seconds,
        max_power_W=simulation.max_power_W,
        avg_power_W=simulation.avg_power_W,
        min_altitude_km=simulation.min_altitude_km,
        max_altitude_km=simulation.max_altitude_km,
        eclipse_time_seconds=simulation.eclipse_time_seconds,
        eclipse_percentage=simulation.eclipse_percentage,
        orbital_period_minutes=simulation.orbital_period_minutes,
        total_data_points=simulation.total_data_points,
        plot_url=simulation.plot_url,
        csv_url=simulation.csv_url
    )