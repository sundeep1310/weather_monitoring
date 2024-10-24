import pytest
from datetime import datetime, timedelta
from src.data_processor import DataProcessor, WeatherRecord
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    WeatherRecord.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal()
    
    WeatherRecord.metadata.drop_all(bind=engine)

def test_store_weather_data(test_db):
    processor = DataProcessor("sqlite:///./test.db")
    
    test_data = {
        "city": "Delhi",
        "main_weather": "Clear",
        "temperature": 25.6,
        "feels_like": 26.1,
        "humidity": 65.0,
        "wind_speed": 3.5,
        "timestamp": datetime.now()
    }
    
    processor.store_weather_data(test_data)
    
    # Query the database to verify
    stored_record = test_db.query(WeatherRecord).first()
    assert stored_record is not None
    assert stored_record.city == "Delhi"
    assert stored_record.temperature == 25.6

def test_get_daily_summary(test_db):
    processor = DataProcessor("sqlite:///./test.db")
    
    # Add test data for multiple timestamps in a day
    base_time = datetime.now().replace(hour=12, minute=0, second=0)
    test_data = [
        {
            "city": "Delhi",
            "main_weather": "Clear",
            "temperature": 25.0,
            "feels_like": 26.0,
            "humidity": 65.0,
            "wind_speed": 3.5,
            "timestamp": base_time
        },
        {
            "city": "Delhi",
            "main_weather": "Clear",
            "temperature": 27.0,
            "feels_like": 28.0,
            "humidity": 60.0,
            "wind_speed": 4.0,
            "timestamp": base_time + timedelta(hours=3)
        }
    ]
    
    for data in test_data:
        processor.store_weather_data(data)
    
    summary = processor.get_daily_summary("Delhi", base_time)
    
    assert summary is not None
    assert summary["city"] == "Delhi"
    assert summary["avg_temp"] == 26.0
    assert summary["max_temp"] == 27.0
    assert summary["min_temp"] == 25.0
    assert summary["dominant_weather"] == "Clear"