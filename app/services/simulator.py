import uuid
import os
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Optional
from app.schemas import SimulationRequest, SimulationResponse, SimulationStatistics, DataPoint
from app.config import settings
from app.services.orbit_propagator import CircularOrbitPropagator, TLEOrbitPropagator, SolarPanelSimulator, OrbitPropagator
from app.database import get_db, SessionLocal
from app.models import Simulation

class SimulationService:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def run_simulation(self, request: SimulationRequest) -> SimulationResponse:
        sim_id = str(uuid.uuid4())
        
        try:
            if request.propagation_method == "circular":
                propagator = CircularOrbitPropagator(
                    altitude_km=request.altitude_km,
                    inclination_deg=request.inclination_deg,
                    start_time=request.start_time
                )
            else:
                propagator = TLEOrbitPropagator(
                    tle_line1=request.tle_line1,
                    tle_line2=request.tle_line2,
                    satellite_name=f"SAT_{sim_id[:8]}"
                )
            
            simulator = SolarPanelSimulator(
                orbit_propagator=propagator,
                panel_area_m2=request.panel_area_m2,
                panel_efficiency=request.panel_efficiency
            )
            
            results_df = simulator.run_simulation(
                start_time=request.start_time,
                duration_hours=request.duration_hours,
                time_step_seconds=request.time_step_seconds
            )
            
            statistics = self.calculate_statistics(results_df, propagator, request.time_step_seconds)
            
            plot_url = None
            csv_url = None
            
            if request.generate_plot:
                plot_url = self.generate_plot(sim_id, results_df, request.propagation_method)
            
            if request.export_csv:
                csv_url = self.export_csv(sim_id, results_df)
            
            data_points = self.prepare_data_points(results_df, max_points=500)

            self.save_to_database(
                sim_id=sim_id,
                request=request,
                statistics=statistics,
                plot_url=plot_url,
                csv_url=csv_url,
                status="success"
            )            
            
            return SimulationResponse(
                simulation_id=sim_id,
                status="success",
                message="Simulation completed successfully",
                statistics=statistics,
                data_points=data_points,
                plot_url=plot_url,
                csv_url=csv_url,
                created_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            self._save_to_database(
                sim_id=sim_id,
                request=request,
                statistics=None,
                plot_url=None,
                csv_url=None,
                status="error",
                error_message=str(e)
            )

            return SimulationResponse(
                simulation_id=sim_id,
                status="error",
                message=f"Simulation failed: {str(e)}",
                created_at=datetime.utcnow().isoformat()
            )
    
    def calculate_statistics(self, df: pd.DataFrame, propagator: OrbitPropagator, time_step_seconds: int) -> SimulationStatistics:
        shadow_count = df['in_shadow'].sum()
        return SimulationStatistics(
            max_power_W=float(df['power_W'].max()),
            avg_power_W=float(df['power_W'].mean()),
            min_altitude_km=float(df['altitude_km'].min()),
            max_altitude_km=float(df['altitude_km'].max()),
            eclipse_time_seconds=float(shadow_count * time_step_seconds),
            eclipse_percentage=float(shadow_count / len(df) * 100),
            orbital_period_minutes=float(propagator.get_orbital_period()),
            total_data_points=len(df)
        )
    
    def prepare_data_points(self, df: pd.DataFrame, max_points: int = 500) -> list[DataPoint]:
        if len(df) > max_points:
            step = len(df) // max_points
            df = df.iloc[::step]
        
        data_points = []
        for _, row in df.iterrows():
            data_points.append(DataPoint(
                time=row['time'].isoformat(),
                power_W=float(row['power_W']),
                in_shadow=bool(row['in_shadow']),
                sun_angle_deg=float(row['sun_angle_deg']),
                altitude_km=float(row['altitude_km'])
            ))
        
        return data_points
    
    def generate_plot(self, sim_id: str, df: pd.DataFrame, method: str) -> str:
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # Power plot
        ax1 = axes[0]
        ax1.plot(df['time'], df['power_W'], 'b-', linewidth=1.5)
        ax1.fill_between(df['time'], 0, df['power_W'], alpha=0.3)
        ax1.set_ylabel('Power (W)')
        ax1.set_title(f'Solar Panel Power Output ({method.upper()})')
        ax1.grid(True, alpha=0.3)
        
        # Sun angle plot
        ax2 = axes[1]
        ax2.plot(df['time'], df['sun_angle_deg'], 'r-', linewidth=1.5)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Sun Angle (°)')
        ax2.set_title('Sun Angle')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        filename = f"{sim_id}_plot.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return f"/outputs/{filename}"
    
    def export_csv(self, sim_id: str, df: pd.DataFrame) -> str:
        """Export results to CSV"""
        filename = f"{sim_id}_data.csv"
        filepath = os.path.join(self.output_dir, filename)
        df.to_csv(filepath, index=False)
        return f"/outputs/{filename}"

    def _save_to_database(
        self,
        sim_id: str,
        request: SimulationRequest,
        statistics: Optional[SimulationStatistics],
        plot_url: Optional[str],
        csv_url: Optional[str],
        status: str,
        error_message: Optional[str] = None
    ):
        """Save simulation record to database"""
        db = SessionLocal()
        try:
            stats_dict = {
                'max_power_W': None,
                'avg_power_W': None,
                'min_altitude_km': None,
                'max_altitude_km': None,
                'eclipse_time_seconds': None,
                'eclipse_percentage': None,
                'orbital_period_minutes': None,
                'total_data_points': None
            }
            if statistics:
                stats_dict = {
                    'max_power_W': statistics.max_power_W,
                    'avg_power_W': statistics.avg_power_W,
                    'min_altitude_km': statistics.min_altitude_km,
                    'max_altitude_km': statistics.max_altitude_km,
                    'eclipse_time_seconds': statistics.eclipse_time_seconds,
                    'eclipse_percentage': statistics.eclipse_percentage,
                    'orbital_period_minutes': statistics.orbital_period_minutes,
                    'total_data_points': statistics.total_data_points
                }
            
            sim_record = Simulation(
                simulation_id=sim_id,
                created_at=datetime.utcnow(),
                propagation_method=request.propagation_method,
                altitude_km=request.altitude_km,
                inclination_deg=request.inclination_deg,
                tle_line1=request.tle_line1,
                tle_line2=request.tle_line2,
                panel_area_m2=request.panel_area_m2,
                panel_efficiency=request.panel_efficiency,
                start_time=request.start_time,
                duration_hours=request.duration_hours,
                time_step_seconds=request.time_step_seconds,
                **stats_dict,
                plot_url=plot_url,
                csv_url=csv_url,
                status=status,
                error_message=error_message
            )
            db.add(sim_record)
            db.commit()
        except Exception as e:
            db.rollback()

        finally:
            db.close()    