import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from .data_processor import WeatherRecord

class WeatherVisualization:
    def __init__(self, data_processor):
        self.data_processor = data_processor

    def create_temperature_chart(self, city: str, days: int = 7) -> Optional[go.Figure]:
        """Create temperature trend visualization."""
        session = self.data_processor.Session()
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp.between(start_date, end_date)
            ).order_by(WeatherRecord.timestamp).all()
            
            if not records:
                return self.create_empty_chart(
                    f'Temperature Trends for {city}',
                    "No temperature data available for this period. Data will appear here once collected."
                )

            df = pd.DataFrame([{
                'timestamp': r.timestamp,
                'temperature': r.temperature,
                'feels_like': r.feels_like
            } for r in records])
            
            fig = go.Figure()
            
            # Actual temperature
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['temperature'],
                name='Actual Temperature',
                line=dict(color='red', width=2),
                mode='lines+markers'
            ))
            
            # Feels like temperature
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['feels_like'],
                name='Feels Like',
                line=dict(color='blue', width=2, dash='dash'),
                mode='lines'
            ))
            
            fig.update_layout(
                title=f'Temperature Trends for {city}',
                xaxis_title='Time',
                yaxis_title='Temperature (°C)',
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            return fig
        
        finally:
            session.close()

    def create_weather_distribution(self, city: str, days: int = 7) -> Optional[go.Figure]:
        """Create weather distribution visualization."""
        session = self.data_processor.Session()
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp.between(start_date, end_date)
            ).all()
            
            if not records:
                return self.create_empty_chart(
                    f'Weather Distribution for {city}',
                    "No weather distribution data available yet. Data will appear here once collected."
                )
            
            weather_counts = pd.Series([r.main_weather for r in records]).value_counts()
            
            colors = px.colors.qualitative.Set3[:len(weather_counts)]
            
            fig = go.Figure(data=[go.Pie(
                labels=weather_counts.index,
                values=weather_counts.values,
                hole=.3,
                marker=dict(colors=colors)
            )])
            
            fig.update_layout(
                title=f'Weather Distribution for {city} (Last {days} days)',
                annotations=[dict(text='Weather Types', x=0.5, y=0.5, font_size=15, showarrow=False)],
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            return fig
            
        finally:
            session.close()

    def create_hourly_chart(self, city: str, hours: int = 24) -> Optional[go.Figure]:
        """Create hourly weather chart."""
        session = self.data_processor.Session()
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=hours)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp.between(start_date, end_date)
            ).order_by(WeatherRecord.timestamp).all()
            
            if not records:
                return self.create_empty_chart(
                    f'Hourly Weather for {city}',
                    "No hourly data available yet. Data will appear here once collected."
                )
            
            # Create DataFrame with only numeric data
            df = pd.DataFrame([{
                'timestamp': r.timestamp,
                'temperature': r.temperature,
                'humidity': r.humidity,
                'wind_speed': r.wind_speed
            } for r in records])
            
            fig = go.Figure()

            # Temperature trace
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['temperature'],
                name='Temperature (°C)',
                line=dict(color='red', width=2),
                mode='lines+markers'
            ))

            # Humidity trace
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['humidity'],
                name='Humidity (%)',
                line=dict(color='blue', width=2),
                mode='lines+markers',
                yaxis='y2'
            ))

            # Wind speed trace
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['wind_speed'],
                name='Wind Speed (m/s)',
                line=dict(color='green', width=2),
                mode='lines+markers',
                yaxis='y3'
            ))
            
            fig.update_layout(
                title=f'Hourly Weather for {city}',
                xaxis=dict(title='Time'),
                yaxis=dict(
                    title='Temperature (°C)',
                    titlefont=dict(color='red'),
                    tickfont=dict(color='red')
                ),
                yaxis2=dict(
                    title='Humidity (%)',
                    titlefont=dict(color='blue'),
                    tickfont=dict(color='blue'),
                    anchor='free',
                    overlaying='y',
                    side='right',
                    position=0.85
                ),
                yaxis3=dict(
                    title='Wind Speed (m/s)',
                    titlefont=dict(color='green'),
                    tickfont=dict(color='green'),
                    anchor='free',
                    overlaying='y',
                    side='right',
                    position=1.0
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            return fig
            
        finally:
            session.close()

    def create_weather_stats(self, city: str, days: int = 7) -> Dict[str, Any]:
        """Create weather statistics."""
        session = self.data_processor.Session()
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            records = session.query(WeatherRecord).filter(
                WeatherRecord.city == city,
                WeatherRecord.timestamp.between(start_date, end_date)
            ).order_by(WeatherRecord.timestamp).all()
            
            if not records:
                return {
                    "message": "No statistical data available yet."
                }
            
            # Create separate lists for numeric data
            temperatures = [r.temperature for r in records]
            humidity_values = [r.humidity for r in records]
            wind_speeds = [r.wind_speed for r in records]
            weather_conditions = [r.main_weather for r in records]
            
            stats = {
                "temperature": {
                    "current": temperatures[-1] if temperatures else None,
                    "avg": sum(temperatures) / len(temperatures) if temperatures else None,
                    "max": max(temperatures) if temperatures else None,
                    "min": min(temperatures) if temperatures else None,
                    "trend": "rising" if len(temperatures) > 1 and temperatures[-1] > temperatures[0] else "falling"
                },
                "humidity": {
                    "current": humidity_values[-1] if humidity_values else None,
                    "avg": sum(humidity_values) / len(humidity_values) if humidity_values else None,
                    "max": max(humidity_values) if humidity_values else None,
                    "min": min(humidity_values) if humidity_values else None
                },
                "wind": {
                    "current": wind_speeds[-1] if wind_speeds else None,
                    "avg": sum(wind_speeds) / len(wind_speeds) if wind_speeds else None,
                    "max": max(wind_speeds) if wind_speeds else None
                },
                "conditions": {
                    "most_common": max(set(weather_conditions), key=weather_conditions.count) if weather_conditions else None
                }
            }
            
            # Round all numeric values
            for category in stats.values():
                if isinstance(category, dict):
                    for key, value in category.items():
                        if isinstance(value, (int, float)):
                            category[key] = round(value, 1)
            
            return stats
            
        finally:
            session.close()

    def create_empty_chart(self, title: str, message: str = "No data available yet.") -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title=title,
            showlegend=False
        )
        return fig