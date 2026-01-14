import numpy as np
from datetime import datetime, timedelta
from skyfield.api import load, EarthSatellite
import pandas as pd
from abc import ABC, abstractmethod

class OrbitPropagator(ABC):

    # Generate satellite position at a given time
    @abstractmethod
    def get_position(self, time_dt):
        pass

    # Get orbital period in minutes
    @abstractmethod
    def get_orbital_period(self):
        pass

class CircularOrbitPropagator(OrbitPropagator):

    def __init__(self, altitude_km, inclination_deg, start_time):
        """
        altitude_km: distance between the earth surface and the satellite
        inclination_deg: orbit tilt (0=equator, 90=polar)
        start_time: ISO format string "2024-01-15T00:00:00"
        """
        self.altitude_km = altitude_km
        self.inclination_deg = inclination_deg
        self.start_dt = datetime.fromisoformat(start_time)
        
        # Earth constants
        self.EARTH_RADIUS_KM = 6371
        self.EARTH_MU = 398600.4418  # km³/s² (Earth's gravitational parameter)
        
        # Orbital radius calculation 
        self.orbital_radius = self.EARTH_RADIUS_KM + self.altitude_km
        
        # Using Kepler's third law: T = 2π√(r³/μ) to determine the orbital period
        period_seconds = 2 * np.pi * np.sqrt(self.orbital_radius**3 / self.EARTH_MU)
        self.orbital_period_minutes = period_seconds / 60
        
        # Angular velocity (rad/s)
        self.angular_velocity = 2 * np.pi / period_seconds
        
    def get_position(self, time_dt):

        # Time elapsed since start
        elapsed = (time_dt - self.start_dt).total_seconds()
        
        # Angle around orbit
        theta = self.angular_velocity * elapsed
        
        # Position in orbital plane (2D circle)
        x_orbit = self.orbital_radius * np.cos(theta)
        y_orbit = self.orbital_radius * np.sin(theta)
        z_orbit = 0
        
        # Rotate by inclination to get 3D position
        inc_rad = np.radians(self.inclination_deg)
        
        # Rotation matrix around X-axis
        x = x_orbit
        y = y_orbit * np.cos(inc_rad) - z_orbit * np.sin(inc_rad)
        z = y_orbit * np.sin(inc_rad) + z_orbit * np.cos(inc_rad)
        
        return np.array([x, y, z])
    
    def get_orbital_period(self):
        return self.orbital_period_minutes

# Using SGP4 algorithm from skyfield library to determine satelitte position from earth     
class TLEOrbitPropagator(OrbitPropagator):
    def __init__(self, tle_line1, tle_line2, satellite_name="SAT"):
        """
        tle_line1: First line of TLE
        tle_line2: Second line of TLE
        satellite_name: Name for reference
        """
        self.ts = load.timescale()
        self.satellite = EarthSatellite(tle_line1, tle_line2, satellite_name, self.ts)
        
        # Extract orbital period from mean motion (in line 2)
        mean_motion = float(tle_line2[52:63])  # revolutions per day
        self.orbital_period_minutes = (24 * 60) / mean_motion
        
        # Extract other parameters for info
        self.inclination = float(tle_line2[8:16])
        self.eccentricity = float('0.' + tle_line2[26:33])
    
    def get_position(self, time_dt):

        # Convert to Skyfield time
        t = self.ts.utc(time_dt.year, time_dt.month, time_dt.day,time_dt.hour, time_dt.minute, time_dt.second)
        
        # Propagate using SGP4
        geocentric = self.satellite.at(t)
        position = geocentric.position.km
        
        return position
    
    def get_orbital_period(self):
        return self.orbital_period_minutes
    
class SolarPanelSimulator:

    def __init__(self, orbit_propagator, panel_area_m2, panel_efficiency):
        """
        orbit_propagator: CircularOrbitPropagator or TLEOrbitPropagator
        panel_area_m2: solar panel size (e.g., 15)
        panel_efficiency: 0.29 means 29%
        """
        self.propagator = orbit_propagator
        self.panel_area = panel_area_m2
        self.efficiency = panel_efficiency
        
        # Constants
        self.SOLAR_CONSTANT = 1361  # W/m²
        self.EARTH_RADIUS_KM = 6371
        
        # Load astronomical data
        self.ts = load.timescale()
        self.planets = load('de421.bsp')
        self.earth = self.planets['earth']
        self.sun = self.planets['sun']
    
    def get_sun_direction(self, time_dt):
        # Generate unit vector from Earth to Sun 
        t = self.ts.utc(time_dt.year, time_dt.month, time_dt.day, time_dt.hour, time_dt.minute, time_dt.second)
        
        sun_position = self.earth.at(t).observe(self.sun).position.km
        sun_direction = sun_position / np.linalg.norm(sun_position)
        
        return sun_direction
    
    def is_in_shadow(self, satellite_pos, sun_direction):
        """
        Check if Earth blocks sunlight using dot product
        If satellite on sunlit side, satellite not in shadow
        If satellite on dark side, check if Earth blocks view
        """
        # Normalize satellite position
        sat_distance = np.linalg.norm(satellite_pos)
        sat_direction = satellite_pos / sat_distance
        
        # Dot product: positive = same side as sun
        dot = np.dot(sat_direction, sun_direction)
        
        if dot > 0:
            # Satellite on sunlit side of Earth
            return False
        else:
            # Satellite on dark side - check if Earth blocks sun
            # Distance from Earth-Sun line to satellite
            projection = np.dot(satellite_pos, sun_direction)
            perpendicular_distance = np.sqrt(sat_distance**2 - projection**2)
            
            return perpendicular_distance < self.EARTH_RADIUS_KM
    
    def calculate_power(self, satellite_pos, sun_direction, in_shadow):
        """
        Power = Solar_Constant x Area x Efficiency x cos(angle)
        """
        if in_shadow:
            return 0.0
        
        # Panel normal (points away from Earth - anti-nadir)
        panel_normal = satellite_pos / np.linalg.norm(satellite_pos)
        
        # Angle between panel and sun
        cos_angle = np.dot(panel_normal, sun_direction)
        
        # Only generate power if sun hits front of panel
        if cos_angle > 0:
            power = self.SOLAR_CONSTANT * self.panel_area * self.efficiency * cos_angle
            return power
        else:
            return 0.0
    
    def run_simulation(self, start_time, duration_hours=3, time_step_seconds=60):
        results = []
        start_dt = datetime.fromisoformat(start_time)
        current_dt = start_dt
        end_dt = start_dt + timedelta(hours=duration_hours)
        step = timedelta(seconds=time_step_seconds)
        
        step_count = 0
        while current_dt <= end_dt:
            # Get satellite position (works with ANY propagator!)
            sat_pos = self.propagator.get_position(current_dt)
            
            # Get sun direction
            sun_dir = self.get_sun_direction(current_dt)
            
            # Check shadow
            in_shadow = self.is_in_shadow(sat_pos, sun_dir)
            
            # Calculate power
            power = self.calculate_power(sat_pos, sun_dir, in_shadow)
            
            # Calculate additional metrics
            panel_normal = sat_pos / np.linalg.norm(sat_pos)
            sun_angle_deg = np.degrees(np.arccos(np.clip(np.dot(panel_normal, sun_dir), -1, 1)))
            altitude = np.linalg.norm(sat_pos) - self.EARTH_RADIUS_KM
            
            results.append({
                'time': current_dt,
                'power_W': power,
                'in_shadow': in_shadow,
                'sun_angle_deg': sun_angle_deg,
                'altitude_km': altitude,
                'position_x': sat_pos[0],
                'position_y': sat_pos[1],
                'position_z': sat_pos[2]
            })
            
            current_dt += step
            step_count += 1
        
        df = pd.DataFrame(results)
        
        return df