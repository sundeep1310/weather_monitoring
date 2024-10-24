from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, func, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, Optional, List, Any
import pandas as pd
from .config import settings
from .database import Base, engine, SessionLocal

class WeatherRecord(Base):
    __tablename__ = "weather_records"
    
    id = Column(Integer, primary_key=True)
    city = Column(String)
    main_weather = Column(String)
    temperature = Column(Float)
    feels_like = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    timestamp = Column(DateTime, index=True)

    __table_args__ = (
        Index('idx_weather_city_timestamp', 'city', 'timestamp'),
        Index('idx_weather_temperature', 'temperature'),
    )

class CityPreference(Base):
    __tablename__ = "city_preferences"
    
    id = Column(Integer, primary_key=True)
    city = Column(String, unique=True)
    country = Column(String, default="IN")
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    alert_threshold = Column(Float, nullable=True)
    custom_settings = Column(Text, nullable=True)  # JSON string for custom settings

class WeatherAlert(Base):
    __tablename__ = "weather_alerts"
    
    id = Column(Integer, primary_key=True)
    city = Column(String)
    alert_type = Column(String)  # 'temperature', 'wind', 'humidity', etc.
    threshold_value = Column(Float)
    actual_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    alert_message = Column(Text)
    snoozed_until = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_alerts_city_timestamp', 'city', 'timestamp'),
        Index('idx_alerts_acknowledged', 'acknowledged'),
    )

class DataProcessor:
    def __init__(self, db_url=None):
        """Initialize the DataProcessor with database connection."""
        self.engine = engine
        Base.metadata.create_all(self.engine)
        self.Session = SessionLocal

    def store_weather_data(self, data: Dict[str, Any]) -> None:
        """Store weather data in the database."""
        session = self.Session()
        try:
            record = WeatherRecord(
                city=data['city'],
                main_weather=data['main_weather'],
                temperature=data['temperature'],
                feels_like=data['feels_like'],
                humidity=data['humidity'],
                wind_speed=data['wind_speed'],
                timestamp=data['timestamp']
            )
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def determine_dominant_weather(self, weather_records: List[Dict]) -> Dict[str, Any]:
        """
        Determine the dominant weather condition using a weighted scoring system.
        
        Logic:
        1. Recent Priority: More recent weather conditions are weighted more heavily
        2. Duration Impact: Longer-lasting conditions have more significance
        3. Severity Priority: Certain weather conditions take precedence based on severity
        """
        if not weather_records:
            return {"condition": None, "confidence": 0, "duration": 0}

        # Weather severity weights (higher = more severe)
        severity_weights = {
            "Thunderstorm": 5,
            "Snow": 4,
            "Rain": 3,
            "Drizzle": 2,
            "Fog": 2,
            "Clouds": 1,
            "Clear": 1,
            "Mist": 1,
            "Haze": 1
        }

        # Calculate time-weighted frequencies
        weather_scores = {}
        total_weight = 0
        now = datetime.utcnow()

        for record in weather_records:
            # Calculate time weight (more recent = higher weight)
            time_diff = (now - record['timestamp']).total_seconds() / 3600  # hours
            time_weight = 1 / (1 + time_diff)  # decay function
            
            # Get severity weight
            severity = severity_weights.get(record['main_weather'], 1)
            
            # Combined weight
            weight = time_weight * severity
            
            weather_scores[record['main_weather']] = weather_scores.get(record['main_weather'], 0) + weight
            total_weight += weight

        if not weather_scores:
            return {"condition": None, "confidence": 0, "duration": 0}

        # Calculate dominant weather
        dominant_weather = max(weather_scores.items(), key=lambda x: x[1])
        
        # Calculate confidence score (0-100%)
        confidence = (dominant_weather[1] / total_weight) * 100 if total_weight > 0 else 0
        
        # Calculate duration of dominant condition
        duration_hours = self.calculate_condition_duration(weather_records, dominant_weather[0])

        return {
            "condition": dominant_weather[0],
            "confidence": round(confidence, 2),
            "duration": duration_hours,
            "severity": severity_weights.get(dominant_weather[0], 1)
        }

    def calculate_condition_duration(self, records: List[Dict], condition: str) -> float:
        """Calculate how long a weather condition has been present in hours."""
        if not records:
            return 0

        records = sorted(records, key=lambda x: x['timestamp'])
        current_duration = 0
        max_duration = 0
        prev_timestamp = None

        for record in records:
            if record['main_weather'] == condition:
                if prev_timestamp:
                    time_diff = (record['timestamp'] - prev_timestamp).total_seconds() / 3600
                    if time_diff <= 6:  # Consider gaps of up to 6 hours as continuous
                        current_duration += time_diff
                    else:
                        current_duration = 0
                prev_timestamp = record['timestamp']
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
                prev_timestamp = None

        return round(max_duration, 1)

    def get_daily_summary(self, city: str, date: datetime) -> Optional[Dict]:
        """Get daily summary for a specific city."""
        session = self.Session()
        try:
            start_date = date.replace(hour=0, minute=0, second=0)
            end_date = start_date + timedelta(days=1)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp >= start_date,
                WeatherRecord.timestamp < end_date
            ).all()
            
            if not records:
                return None
                
            record_dicts = [{
                'timestamp': r.timestamp,
                'main_weather': r.main_weather,
                'temperature': r.temperature,
                'humidity': r.humidity,
                'wind_speed': r.wind_speed
            } for r in records]
            
            weather_analysis = self.determine_dominant_weather(record_dicts)
            temperatures = [r.temperature for r in records]
            
            summary = {
                "city": city,
                "date": start_date.date(),
                "avg_temp": sum(temperatures) / len(temperatures),
                "max_temp": max(temperatures),
                "min_temp": min(temperatures),
                "weather_analysis": {
                    "dominant_condition": weather_analysis["condition"],
                    "confidence": weather_analysis["confidence"],
                    "duration_hours": weather_analysis["duration"],
                    "severity_level": weather_analysis["severity"]
                },
                "avg_humidity": sum(r.humidity for r in records) / len(records),
                "avg_wind_speed": sum(r.wind_speed for r in records) / len(records)
            }
            return summary
        finally:
            session.close()

    def get_cities(self) -> List[Dict[str, str]]:
        """Get list of active cities."""
        session = self.Session()
        try:
            cities = session.query(CityPreference).filter_by(is_active=True).all()
            return [{"city": c.city, "country": c.country} for c in cities]
        finally:
            session.close()

    def add_city(self, city: str, country: str = "IN") -> None:
        """Add a new city to monitor."""
        session = self.Session()
        try:
            existing_city = session.query(CityPreference).filter_by(city=city).first()
            if existing_city:
                if not existing_city.is_active:
                    existing_city.is_active = True
                    existing_city.country = country
                    session.commit()
                return
            
            city_pref = CityPreference(city=city, country=country)
            session.add(city_pref)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def remove_city(self, city: str) -> None:
        """Remove a city from monitoring."""
        session = self.Session()
        try:
            city_pref = session.query(CityPreference).filter_by(city=city).first()
            if city_pref:
                city_pref.is_active = False
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def acknowledge_alert(self, alert_id: int, acknowledged: bool = True) -> bool:
        """Acknowledge or unacknowledge a weather alert."""
        session = self.Session()
        try:
            alert = session.query(WeatherAlert).filter_by(id=alert_id).first()
            if alert:
                alert.acknowledged = acknowledged
                alert.acknowledged_at = datetime.utcnow() if acknowledged else None
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error acknowledging alert: {str(e)}")
            return False
        finally:
            session.close()

    def snooze_alert(self, alert_id: int, duration: int) -> bool:
        """Snooze an alert for a specified duration in minutes."""
        session = self.Session()
        try:
            alert = session.query(WeatherAlert).filter_by(id=alert_id).first()
            if alert:
                alert.snoozed_until = datetime.utcnow() + timedelta(minutes=duration)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error snoozing alert: {str(e)}")
            return False
        finally:
            session.close()

    def get_active_alerts_count(self) -> int:
        """Get count of active (unacknowledged and not snoozed) alerts."""
        session = self.Session()
        try:
            return session.query(WeatherAlert).filter(
                WeatherAlert.acknowledged == False,
                (WeatherAlert.snoozed_until.is_(None) | 
                 (WeatherAlert.snoozed_until < datetime.utcnow()))
            ).count()
        finally:
            session.close()

    def get_alert_history(
        self,
        start_date: datetime,
        end_date: datetime,
        city: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Dict]:
        """Get alert history with filters."""
        session = self.Session()
        try:
            query = session.query(WeatherAlert).filter(
                WeatherAlert.timestamp.between(start_date, end_date)
            )
            
            if city:
                query = query.filter(WeatherAlert.city == city)
            if acknowledged is not None:
                query = query.filter(WeatherAlert.acknowledged == acknowledged)
                
            alerts = query.order_by(WeatherAlert.timestamp.desc()).all()
            
            return [{
                'id': alert.id,
                'city': alert.city,
                'alert_type': alert.alert_type,
                'threshold_value': alert.threshold_value,
                'actual_value': alert.actual_value,
                'timestamp': alert.timestamp,
                'acknowledged': alert.acknowledged,
                'acknowledged_at': alert.acknowledged_at,
                'message': alert.alert_message,
                'snoozed_until': alert.snoozed_until
            } for alert in alerts]
        finally:
            session.close()

    def get_weather_trends(self, city: str, days: int = 7) -> Dict[str, Any]:
        """Get weather trends for a specific city."""
        session = self.Session()
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp.between(start_date, end_date)
            ).order_by(WeatherRecord.timestamp).all()
            
            if not records:
                return {}
                
            # Convert to pandas DataFrame for easier analysis
            df = pd.DataFrame([{
                'temperature': r.temperature,
                'humidity': r.humidity,
                'wind_speed': r.wind_speed,
                'timestamp': r.timestamp,
                'main_weather': r.main_weather
            } for r in records])
            
            return {
                'temperature_trend': {
                    'min': df['temperature'].min(),
                    'max': df['temperature'].max(),
                    'avg': df['temperature'].mean(),
                    'trend': 'rising' if df['temperature'].iloc[-1] > df['temperature'].iloc[0] else 'falling'
                },
                'humidity_trend': {
                    'min': df['humidity'].min(),
                    'max': df['humidity'].max(),
                    'avg': df['humidity'].mean()
                },
                'wind_trend': {
                    'min': df['wind_speed'].min(),
                    'max': df['wind_speed'].max(),
                    'avg': df['wind_speed'].mean()
                },
                'weather_distribution': df['main_weather'].value_counts().to_dict()
            }
        finally:
            session.close()