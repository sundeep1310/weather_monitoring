import pytest
import aiohttp
from aioresponses import aioresponses
from datetime import datetime
from src.weather_service import WeatherService

@pytest.fixture
async def weather_service():
    """Fixture to provide a WeatherService instance."""
    async with WeatherService() as service:
        yield service

@pytest.mark.asyncio
async def test_get_weather_data(weather_service):
    """Test successful weather data retrieval."""
    with aioresponses() as m:
        # Mock API response
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=Delhi,IN&appid=test_key&units=metric",
            payload={
                "weather": [{"main": "Clear"}],
                "main": {
                    "temp": 25.6,
                    "feels_like": 26.1,
                    "humidity": 65
                },
                "wind": {"speed": 3.5},
                "dt": int(datetime.now().timestamp())
            },
            status=200
        )
        
        weather_data = await weather_service.get_weather_data("Delhi")
        
        assert weather_data is not None
        assert weather_data["city"] == "Delhi"
        assert weather_data["main_weather"] == "Clear"
        assert isinstance(weather_data["temperature"], float)
        assert isinstance(weather_data["feels_like"], float)

@pytest.mark.asyncio
async def test_get_weather_data_error(weather_service):
    """Test weather data retrieval with error response."""
    with aioresponses() as m:
        # Mock API error response
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=NonexistentCity,IN&appid=test_key&units=metric",
            payload={"message": "city not found"},
            status=404
        )
        
        weather_data = await weather_service.get_weather_data("NonexistentCity")
        assert weather_data is None

@pytest.mark.asyncio
async def test_get_bulk_weather_data(weather_service):
    """Test bulk weather data retrieval."""
    with aioresponses() as m:
        # Mock responses for all cities
        for city in ["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata", "Hyderabad"]:
            m.get(
                f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid=test_key&units=metric",
                payload={
                    "weather": [{"main": "Clear"}],
                    "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 65},
                    "wind": {"speed": 3.5},
                    "dt": int(datetime.now().timestamp())
                },
                status=200
            )
        
        results = await weather_service.get_bulk_weather_data()
        assert len(results) == 6
        assert all(r["main_weather"] == "Clear" for r in results)

@pytest.mark.asyncio
async def test_temperature_conversion(weather_service):
    """Test temperature conversion and formatting."""
    with aioresponses() as m:
        # Test standard case
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            payload={
                "weather": [{"main": "Clear"}],
                "main": {
                    "temp": 25.6,  # Direct Celsius as we use units=metric
                    "feels_like": 26.1,
                    "humidity": 65
                },
                "wind": {"speed": 3.5},
                "dt": int(datetime.now().timestamp())
            },
            status=200
        )
        
        result = await weather_service.get_weather_data("TestCity")
        assert result["temperature"] == 25.6
        assert result["feels_like"] == 26.1

@pytest.mark.asyncio
async def test_temperature_edge_cases(weather_service):
    """Test temperature conversion edge cases."""
    test_cases = [
        (40.0, "Extreme Heat"),  # Very hot
        (-10.0, "Extreme Cold"), # Very cold
        (0.0, "Freezing Point"), # Freezing point
        (37.0, "Body Temperature"), # Normal body temperature
    ]
    
    for temp, case_name in test_cases:
        with aioresponses() as m:
            m.get(
                f"http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
                payload={
                    "weather": [{"main": "Clear"}],
                    "main": {
                        "temp": temp,
                        "feels_like": temp,
                        "humidity": 65
                    },
                    "wind": {"speed": 3.5},
                    "dt": int(datetime.now().timestamp())
                },
                status=200
            )
            
            result = await weather_service.get_weather_data("TestCity")
            assert result["temperature"] == temp, f"Failed for {case_name}"

@pytest.mark.asyncio
async def test_temperature_precision(weather_service):
    """Test temperature conversion precision."""
    with aioresponses() as m:
        # Test precise temperatures
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            payload={
                "weather": [{"main": "Clear"}],
                "main": {
                    "temp": 22.22,
                    "feels_like": 21.67,
                    "humidity": 65
                },
                "wind": {"speed": 3.5},
                "dt": int(datetime.now().timestamp())
            },
            status=200
        )
        
        result = await weather_service.get_weather_data("TestCity")
        assert abs(result["temperature"] - 22.22) < 0.01
        assert abs(result["feels_like"] - 21.67) < 0.01

@pytest.mark.asyncio
async def test_rate_limiting(weather_service):
    """Test API rate limiting behavior."""
    with aioresponses() as m:
        # Mock rate limit response
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            payload={"message": "Rate limit exceeded"},
            status=429,
            headers={'Retry-After': '60'}
        )
        
        result = await weather_service.get_weather_data("TestCity")
        assert result is None  # Should handle rate limiting gracefully

@pytest.mark.asyncio
async def test_connection_error(weather_service):
    """Test handling of connection errors."""
    with aioresponses() as m:
        # Mock connection error
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            exception=aiohttp.ClientError()
        )
        
        result = await weather_service.get_weather_data("TestCity")
        assert result is None  # Should handle connection error gracefully

@pytest.mark.asyncio
async def test_invalid_response(weather_service):
    """Test handling of invalid API responses."""
    with aioresponses() as m:
        # Mock invalid response format
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            payload={"invalid": "response"},
            status=200
        )
        
        result = await weather_service.get_weather_data("TestCity")
        assert result is None  # Should handle invalid response gracefully

@pytest.mark.asyncio
async def test_session_management(weather_service):
    """Test session management functionality."""
    # Test session creation
    assert weather_service.session is not None
    
    # Test session closure
    await weather_service.close()
    assert weather_service.session is None or weather_service.session.closed
    
    # Test session recreation
    await weather_service.ensure_session()
    assert weather_service.session is not None and not weather_service.session.closed

@pytest.mark.asyncio
async def test_cache_behavior(weather_service):
    """Test caching behavior."""
    with aioresponses() as m:
        # Set up initial response
        m.get(
            "http://api.openweathermap.org/data/2.5/weather?q=TestCity,IN&appid=test_key&units=metric",
            payload={
                "weather": [{"main": "Clear"}],
                "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 65},
                "wind": {"speed": 3.5},
                "dt": int(datetime.now().timestamp())
            },
            status=200
        )
        
        # First call should hit the API
        result1 = await weather_service.get_weather_data("TestCity")
        
        # Second call should use cache
        result2 = await weather_service.get_weather_data("TestCity")
        
        assert result1 == result2
        assert weather_service.cache.get(f"TestCity_weather") is not None