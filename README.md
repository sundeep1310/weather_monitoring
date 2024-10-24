# Weather Monitoring System 🌤️

Welcome to the Weather Monitoring System! This app helps you keep track of weather in different cities. Think of it as your personal weather assistant! 🌈

## What Can This App Do? 🎯

- Show you real-time weather for any city 🌍
- Track temperature changes over time 📈
- Show you pretty charts and graphs 📊
- Send email alerts when the weather gets too hot! 🌡️
- Store historical weather data 📅

## Let's Get Started! 🚀

### Step 1: Things You Need First (Prerequisites)

- Python (version 3.8 or higher) 🐍
- Docker (for running our database) 🐋
- A free OpenWeather API key (I'll show you how to get this!) 🔑
- A Gmail account for sending alerts (or another email service) 📧

### Step 2: Getting Your OpenWeather API Key

1. Go to [OpenWeatherMap](https://openweathermap.org/api)
2. Click "Sign Up" and create a free account
3. Once logged in, go to "API Keys"
4. Copy your API key (it looks like a long string of letters and numbers)

### Step 3: Setting Up The Project

1. First, let's get the code on your computer! Open your terminal and type:

```bash
# Clone this project to your computer
git clone https://github.com/your-username/weather-monitoring.git

# Go into the project folder
cd weather-monitoring

# Create a special environment for our app
python -m venv venv

# Activate the environment
# For Windows:
venv\Scripts\activate
# For Mac/Linux:
source venv/bin/activate
```

2. Install all the tools we need:

```bash
pip install -r requirements.txt
```

### Step 4: Setting Up The Database

1. Make sure Docker is running on your computer
2. Open your terminal and type:

```bash
# Start the database
docker-compose up -d
```

### Step 5: Setting Up Your Environment

1. Create a new file called `.env` in your project folder
2. Put these settings in it (replace with your details!):

```env
# API Settings
OPENWEATHERMAP_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/weather_db

# Update Settings
UPDATE_INTERVAL=300  # Time in seconds (300 = 5 minutes)

# Alert Settings
ALERT_TEMPERATURE_THRESHOLD=35.0
CONSECUTIVE_ALERTS_REQUIRED=2

# Email Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your_app_password
```

### Step 6: Setting Up Email Alerts 📧

#### Getting Your Google App Password

If you're using Gmail, you'll need a special app password:

1. Go to your Google Account settings
2. Click on 'Security'
3. Under 'Signing in to Google', click on '2-Step Verification'
4. At the bottom, click on 'App passwords'
5. Select 'Mail' and 'Other (Custom name)'
6. Name it 'Weather Monitor'
7. Click 'Generate'
8. Copy the 16-character password
9. Use this as your SMTP_PASSWORD in the .env file

#### How Alerts Work

- When temperature goes above your threshold
- System checks if it stays hot (based on CONSECUTIVE_ALERTS_REQUIRED)
- Sends you an email alert with the details
- Keeps tracking until temperature drops

### Step 7: Starting The App

1. Make sure you're in the project folder
2. Type this in your terminal:

```bash
python -m uvicorn main:app --reload
```

3. Open your web browser
4. Go to: http://localhost:8000
5. You should see your weather dashboard! 🎉

### Step 8: Using The App

#### Adding Cities

1. Type a city name in the box at the top
2. Click "Add City" or press Enter
3. The city will appear in the list
4. Click on the city to see its weather details

#### Viewing Weather Information

Each city shows:

- Current temperature
- How it feels
- Humidity levels
- Wind speed
- Weather conditions
- Historical trends in charts

#### Managing Cities

- Click any city to view its details
- Use the "x" button to stop tracking a city
- Add multiple cities to compare weather

#### Understanding the Charts

1. **Temperature Trends**: Shows temperature changes over time
2. **Weather Distribution**: Shows common weather patterns
3. **Hourly Weather**: Shows detailed 24-hour forecast
4. **Statistics Panel**: Shows highs, lows, and averages

### Need Help? 🆘

#### Common Issues and Fixes

1. **No Cities Showing Up?**

   - Check your database connection
   - Verify your OpenWeather API key
   - Look for errors in the terminal
   - Try adding a city manually

2. **Not Getting Email Alerts?**

   - Check your spam folder
   - Verify email settings in .env
   - Make sure you're using an App Password (for Gmail)
   - Check application logs

3. **Charts Not Loading?**

   - Wait a few minutes for data collection
   - Check your browser console for errors
   - Try refreshing the page

4. **Database Issues?**
   Try these commands:
   ```bash
   # Stop everything
   docker-compose down
   # Clean up old data
   docker-compose down -v
   # Start fresh
   docker-compose up -d
   ```

### For Developers 👩‍💻👨‍💻

#### Project Structure

```
weather-monitoring/
├── src/
│   ├── alerts.py         # Email alert system
│   ├── config.py         # Configuration settings
│   ├── data_processor.py # Data handling
│   ├── visualization.py  # Chart generation
│   └── weather_service.py# API interaction
├── static/              # Static files
├── templates/           # HTML templates
├── main.py             # Main application
├── requirements.txt    # Dependencies
└── docker-compose.yml  # Docker config
```

#### Database Schema

The app uses three main tables:

1. `weather_records`: Stores weather data

   - city, temperature, humidity, etc.
   - timestamp for historical tracking

2. `city_preferences`: Stores city settings

   - city name, country
   - active status
   - custom thresholds

3. `weather_alerts`: Stores alert history
   - alert type
   - timestamp
   - acknowledgment status

### Testing 🧪

Run the test suite:

```bash
# Run all tests
pytest

# Run specific tests
pytest test_weather_service.py
pytest test_alerts.py
```

### Support ❓

If you need help:

1. Check existing issues on GitHub
2. Create a new issue with:
   - What you were trying to do
   - What happened instead
   - Any error messages
   - Your environment details

Happy Weather Monitoring! ☀️🌤️🌦️
