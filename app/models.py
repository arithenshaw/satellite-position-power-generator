from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Simulation(Base):
    """Database model for storing simulation records"""
    __tablename__ = "simulations"
    
    simulation_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Orbit parameters
    propagation_method = Column(String, nullable=False)
    altitude_km = Column(Float, nullable=True)
    inclination_deg = Column(Float, nullable=True)
    tle_line1 = Column(Text, nullable=True)
    tle_line2 = Column(Text, nullable=True)
    
    # Panel parameters
    panel_area_m2 = Column(Float, nullable=False)
    panel_efficiency = Column(Float, nullable=False)
    
    # Simulation parameters
    start_time = Column(String, nullable=False)
    duration_hours = Column(Float, nullable=False)
    time_step_seconds = Column(Integer, nullable=False)
    
    # Results - statistics
    max_power_W = Column(Float, nullable=True)
    avg_power_W = Column(Float, nullable=True)
    min_altitude_km = Column(Float, nullable=True)
    max_altitude_km = Column(Float, nullable=True)
    eclipse_time_seconds = Column(Float, nullable=True)
    eclipse_percentage = Column(Float, nullable=True)
    orbital_period_minutes = Column(Float, nullable=True)
    total_data_points = Column(Integer, nullable=True)
    
    # Output files
    plot_url = Column(String, nullable=True)
    csv_url = Column(String, nullable=True)
    
    # Status
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
