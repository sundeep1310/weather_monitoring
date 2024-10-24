import aiohttp
import asyncio
import backoff
from datetime import datetime
from typing import Dict, Optional, List
from cachetools import TTLCache
from .config import settings

class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHERMAP_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes
        self.session = None
        self._session_lock = asyncio.Lock()
        self.rate_limit = asyncio.Semaphore(10)  # Limit concurrent requests

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def ensure_session(self):
        """Ensure we have a valid session."""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={'Connection': 'keep-alive'}
                )

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def get_weather_data(self, city: str) -> Optional[Dict]:
        """Fetch weather data for a given city with retry logic."""
        # Check cache first
        cache_key = f"{city}_weather"
        if cache_key in self.cache:
            return self.cache[cache_key]

        await self.ensure_session()
        
        params = {
            "q": f"{city},IN",
            "appid": self.api_key,
            "units": "metric"  # Direct Celsius
        }
        
        try:
            async with self.rate_limit:  # Rate limit requests
                async with self.session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        processed_data = {
                            "city": city,
                            "main_weather": data["weather"][0]["main"],
                            "temperature": data["main"]["temp"],
                            "feels_like": data["main"]["feels_like"],
                            "humidity": data["main"]["humidity"],
                            "wind_speed": data["wind"]["speed"],
                            "timestamp": datetime.fromtimestamp(data["dt"])
                        }
                        # Cache the result
                        self.cache[cache_key] = processed_data
                        return processed_data
                    elif response.status == 429:  # Rate limit hit
                        retry_after = int(response.headers.get('Retry-After', '60'))
                        await asyncio.sleep(retry_after)
                        return await self.get_weather_data(city)  # Retry after waiting
                    else:
                        error_data = await response.text()
                        print(f"Error fetching weather data for {city}: {response.status} - {error_data}")
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Connection error for {city}: {str(e)}")
            raise  # Let backoff handle the retry
        except Exception as e:
            print(f"Unexpected error fetching weather data for {city}: {str(e)}")
            return None

    async def get_bulk_weather_data(self) -> List[Dict]:
        """Fetch weather data for multiple cities concurrently with improved error handling."""
        cities = settings.CITIES
        tasks = []
        results = []

        try:
            # Create tasks for each city
            for city in cities:
                tasks.append(self.get_weather_data(city))
            
            # Wait for all tasks to complete
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out errors and None values
            for result in completed_tasks:
                if isinstance(result, dict):  # Only include successful results
                    results.append(result)
            
        except Exception as e:
            print(f"Error in bulk weather data fetch: {str(e)}")
        
        return results

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None