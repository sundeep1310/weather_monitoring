from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uvicorn
from pathlib import Path
import logging

# Import our modules
from src.config import settings
from src.weather_service import WeatherService
from src.data_processor import DataProcessor
from src.alerts import AlertSystem
from src.visualization import WeatherVisualization
from src.database import get_db, engine, Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models
class CityIn(BaseModel):
    """
    Model for adding a new city to monitor.
    """
    city: str
    country: str = "IN"

class AlertConfig(BaseModel):
    """
    Model for configuring alert thresholds.
    """
    temperature_threshold: float = Field(..., gt=0, description="Temperature threshold in Celsius")
    consecutive_required: int = Field(..., ge=1, le=5, description="Number of consecutive readings required to trigger alert")

class AlertAcknowledge(BaseModel):
    """
    Model for acknowledging alerts.
    """
    alert_id: int
    notes: Optional[str] = None

class AlertSnooze(BaseModel):
    """
    Model for snoozing alerts.
    """
    duration: int = Field(..., ge=15, le=1440, description="Snooze duration in minutes (15min to 24hrs)")

# Create the FastAPI app
app = FastAPI(
    title="Weather Monitoring System",
    description="Real-time weather monitoring system with configurable cities",
    version="1.0.0"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Weather Monitoring System API",
        version="1.0.0",
        description="""
        Real-time weather monitoring system with configurable alerts and visualizations.
        
        Features:
        - Real-time weather data collection
        - Configurable alerts
        - Historical data visualization
        - Daily weather summaries
        """,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Set up static files and templates
static_path = Path("static")
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

templates_path = Path("src/dashboard/templates")
templates = Jinja2Templates(directory=str(templates_path))

# Initialize services
weather_service = WeatherService()
data_processor = DataProcessor(settings.DATABASE_URL)
alert_system = AlertSystem()
visualizer = WeatherVisualization(data_processor)

# Background Tasks
async def fetch_city_weather(city: str):
    """Fetch weather data for a single city."""
    try:
        async with weather_service as service:
            data = await service.get_weather_data(city)
            if data:
                data_processor.store_weather_data(data)
                # Check for alerts
                await alert_system.check_temperature_alert(
                    data["city"], 
                    data["temperature"]
                )
                
                # Check other conditions (wind, humidity, etc.)
                await alert_system.check_weather_conditions(data)
    except Exception as e:
        logger.error(f"Error fetching data for {city}: {str(e)}")

async def fetch_weather_data():
    """Background task to periodically fetch weather data for all cities."""
    while True:
        try:
            cities = data_processor.get_cities()
            tasks = []
            for city_info in cities:
                task = fetch_city_weather(city_info["city"])
                tasks.append(task)
            
            if tasks:
                # Execute all city fetches concurrently
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error in background task: {str(e)}")
        finally:
            # Wait for next update interval
            await asyncio.sleep(settings.UPDATE_INTERVAL)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Start background tasks when application starts."""
    asyncio.create_task(fetch_weather_data())
    logger.info("Weather monitoring system started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when application shuts down."""
    if weather_service.session:
        await weather_service.close()
    logger.info("Weather monitoring system shutdown")

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Render the main dashboard.
    
    Returns:
        HTMLResponse: The main dashboard page showing current weather conditions and visualizations.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "cities": data_processor.get_cities()
        }
    )

@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    """
    Render the alerts dashboard.
    
    Returns:
        HTMLResponse: The alerts page showing active and historical alerts.
    """
    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "cities": data_processor.get_cities(),
            "unacknowledged_alerts": data_processor.get_alert_history(
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now(),
                acknowledged=False
            )
        }
    )

@app.get("/api/cities")
async def get_cities():
    """
    Get list of monitored cities.
    
    Returns:
        dict: List of cities being monitored.
        
    Example response:
        {
            "cities": [
                {"city": "Delhi", "country": "IN"},
                {"city": "Mumbai", "country": "IN"}
            ]
        }
    """
    try:
        return {"cities": data_processor.get_cities()}
    except Exception as e:
        logger.error(f"Error getting cities: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving cities")

@app.post("/api/cities")
async def add_city(city: CityIn, background_tasks: BackgroundTasks):
    """
    Add a new city to monitor.
    
    Parameters:
        - city (CityIn): City details including name and country code
        - background_tasks: Background tasks handler
        
    Returns:
        dict: Confirmation message
        
    Raises:
        HTTPException: If city is invalid or already exists
    """
    try:
        # Verify city exists with OpenWeather API
        async with weather_service as service:
            weather = await service.get_weather_data(f"{city.city},{city.country}")
            if not weather:
                raise HTTPException(status_code=404, detail="City not found in OpenWeather API")
        
        # Add city to database
        data_processor.add_city(city.city, city.country)
        
        # Fetch initial data in background
        background_tasks.add_task(fetch_city_weather, city.city)
        
        return {"message": f"Added {city.city} to monitoring"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding city: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/cities/{city}")
async def remove_city(city: str):
    """
    Remove a city from monitoring.
    
    Parameters:
        - city (str): Name of the city to remove
        
    Returns:
        dict: Confirmation message
        
    Raises:
        HTTPException: If city cannot be removed
    """
    try:
        data_processor.remove_city(city)
        return {"message": f"Removed {city} from monitoring"}
    except Exception as e:
        logger.error(f"Error removing city: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/weather/current/{city}")
async def get_current_weather(city: str):
    """
    Get current weather data for a specific city.
    
    Parameters:
        - city (str): Name of the city
        
    Returns:
        dict: Current weather data including temperature, humidity, etc.
        
    Example response:
        {
            "city": "Delhi",
            "temperature": 25.6,
            "humidity": 65,
            "wind_speed": 3.5,
            "main_weather": "Clear"
        }
    """
    try:
        async with weather_service as service:
            data = await service.get_weather_data(city)
            if not data:
                raise HTTPException(status_code=404, detail="Weather data not found")
            return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching weather data")

@app.get("/api/weather/visualization/{city}")
def get_weather_visualization(city: str):
    """
    Get weather visualization data for a specific city.
    
    Parameters:
        - city (str): Name of the city
        
    Returns:
        dict: Visualization data including charts and statistics
    """
    try:
        temp_chart = visualizer.create_temperature_chart(city)
        weather_dist = visualizer.create_weather_distribution(city)
        hourly_chart = visualizer.create_hourly_chart(city)
        weather_stats = visualizer.create_weather_stats(city)
        
        return {
            "temperature_chart": temp_chart.to_json() if temp_chart else None,
            "weather_distribution": weather_dist.to_json() if weather_dist else None,
            "hourly_chart": hourly_chart.to_json() if hourly_chart else None,
            "weather_stats": weather_stats
        }
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate visualizations"
        )

@app.get("/api/weather/summary/{city}")
async def get_weather_summary(city: str):
    """
    Get daily weather summary for a city.
    
    Parameters:
        - city (str): Name of the city
        
    Returns:
        dict: Daily weather summary including averages and extremes
    """
    try:
        summary = data_processor.get_daily_summary(city, datetime.now())
        if not summary:
            raise HTTPException(status_code=404, detail="No data available for summary")
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating summary")

@app.get("/api/alerts/status")
def get_alerts_status():
    """
    Get current alert system status.
    
    Returns:
        dict: Alert system status including counts and thresholds
    """
    try:
        return {
            "alert_counts": data_processor.get_active_alerts_count(),
            "temperature_threshold": settings.ALERT_TEMPERATURE_THRESHOLD,
            "consecutive_required": settings.CONSECUTIVE_ALERTS_REQUIRED,
            "system_status": "operational"
        }
    except Exception as e:
        logger.error(f"Error getting alert status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving alert status")

@app.get("/api/alerts/history")
def get_alerts_history(
    days: int = 7,
    city: Optional[str] = None,
    acknowledged: Optional[bool] = None
):
    """
    Get alert history for the specified number of days.
    
    Parameters:
        - days (int): Number of days of history to retrieve (default: 7)
        - city (str, optional): Filter by city
        - acknowledged (bool, optional): Filter by acknowledgment status
        
    Returns:
        dict: List of historical alerts matching the criteria
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        alerts = data_processor.get_alert_history(
            start_date=start_date,
            end_date=end_date,
            city=city,
            acknowledged=acknowledged
        )
        
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting alert history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving alert history")

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, data: AlertAcknowledge):
    """
    Acknowledge an alert.
    
    Parameters:
        - alert_id (int): ID of the alert to acknowledge
        - data (AlertAcknowledge): Acknowledgment details
        
    Returns:
        dict: Confirmation message
    """
    try:
        success = data_processor.acknowledge_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"message": "Alert acknowledged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Error acknowledging alert")

@app.post("/api/alerts/{alert_id}/snooze")
async def snooze_alert(alert_id: int, data: AlertSnooze):
    """
    Snooze an alert for a specified duration.
    
    Parameters:
        - alert_id (int): ID of the alert to snooze
        - data (AlertSnooze): Snooze duration details
        
    Returns:
        dict: Confirmation message
    """
    try:
        success = data_processor.snooze_alert(alert_id, data.duration)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"message": f"Alert snoozed for {data.duration} minutes"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error snoozing alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Error snoozing alert")

@app.post("/api/alerts/config")
async def update_alert_config(config: AlertConfig):
    """
    Update alert configuration.
    
    Parameters:
        - config (AlertConfig): New alert configuration
        
    Returns:
        dict: Confirmation message
    """
    try:
        settings.ALERT_TEMPERATURE_THRESHOLD = config.temperature_threshold
        settings.CONSECUTIVE_ALERTS_REQUIRED = config.consecutive_required
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating alert config: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating configuration")

@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: System health status including version and database connection status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": app.version,
        "database": "connected" if engine else "disconnected"
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )