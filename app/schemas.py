from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Literal, Optional
from datetime import datetime

class OrbitParametersBase(BaseModel):
    propagation_method: Literal["circular", "tle"] = Field(default="circular", description="Orbit propagation method")
    altitude_km: Optional[float] = Field(default=500, ge=200, le=2000, description="Orbit altitude in km (for circular method)")
    inclination_deg: Optional[float] = Field(default=51.6, ge=0, le=180, description="Orbit inclination in degrees (for circular method)")
    tle_line1: Optional[str] = Field(default=None, description="TLE line 1 (for TLE method)")
    tle_line2: Optional[str] = Field(default=None, description="TLE line 2 (for TLE method)")
    
class PanelParametersBase(BaseModel):
    panel_area_m2: float = Field(default=15.0, ge=1, le=100, description="Solar panel area in square meters")
    panel_efficiency: float = Field( default=0.29, ge=0.1, le=0.5, description="Panel efficiency (0.29 = 29%)")
    
class SimulationParametersBase(BaseModel):
    start_time: str = Field(default="2024-01-15T00:00:00", description="Simulation start time (ISO format)")
    duration_hours: float = Field(default=3.0, ge=0.1, le=24, description="Simulation duration in hours")
    time_step_seconds: int = Field(default=60, ge=1, le=300, description="Time step in seconds")

class SimulationRequest(OrbitParametersBase, PanelParametersBase, SimulationParametersBase):    
    # Output options
    generate_plot: bool = Field(default=True, description="Generate visualization plot")
    export_csv: bool = Field(default=True, description="Export results to CSV")
    
    #validate tle_line1 and tle_line2 is provided when propagtion_method is set to tle
    @model_validator(mode='after')
    def validate_tle_required(self):
        if self.propagation_method == 'tle':
            if not self.tle_line1 or not self.tle_line2:
                raise ValueError("TLE lines (tle_line1 and tle_line2) are required when using TLE propagation")
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "propagation_method": "circular",
                "altitude_km": 500,
                "inclination_deg": 51.6,
                "panel_area_m2": 15.0,
                "panel_efficiency": 0.29,
                "start_time": "2024-01-15T00:00:00",
                "duration_hours": 3.0,
                "time_step_seconds": 60,
                "generate_plot": True,
                "export_csv": True
            }
        }
    )

class DataPoint(BaseModel):
    time: str
    power_W: float
    in_shadow: bool
    sun_angle_deg: float
    altitude_km: float

class SimulationStatistics(BaseModel):
    max_power_W: float
    avg_power_W: float
    min_altitude_km: float
    max_altitude_km: float
    eclipse_time_seconds: float
    eclipse_percentage: float
    orbital_period_minutes: float
    total_data_points: int

class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    message: str
    statistics: Optional[SimulationStatistics] = None
    data_points: Optional[list[DataPoint]] = None
    plot_url: Optional[str] = None
    csv_url: Optional[str] = None
    created_at: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str