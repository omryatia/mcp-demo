#!/usr/bin/env python3
"""
Simple MCP Server using FastMCP - Much cleaner!
"""

import asyncio
import json
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Create FastMCP server - that's it!
mcp = FastMCP("Weather Server")

@mcp.tool()
async def get_weather(city: str) -> Dict[str, Any]:
    """
    Get current weather for a city using free wttr.in API
    
    Args:
        city: Name of the city to get weather for
    
    Returns:
        Weather information including temperature, description, etc.
    """
    try:
        # Use wttr.in - completely free, no API key needed!
        url = f"https://wttr.in/{city}?format=j1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        
        return {
            "city": area["areaName"][0]["value"],
            "country": area["country"][0]["value"],
            "region": area["region"][0]["value"],
            "temperature": f"{current['temp_C']}°C ({current['temp_F']}°F)",
            "feels_like": f"{current['FeelsLikeC']}°C ({current['FeelsLikeF']}°F)",
            "description": current["weatherDesc"][0]["value"],
            "humidity": f"{current['humidity']}%",
            "pressure": f"{current['pressure']} mb",
            "wind_speed": f"{current['windspeedKmph']} km/h",
            "wind_direction": current["winddir16Point"],
            "visibility": f"{current['visibility']} km",
            "uv_index": current["uvIndex"],
            "local_time": data["current_condition"][0]["localObsDateTime"]
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch weather data: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {"error": f"Failed to parse weather data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Optional: Add more tools easily
@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> Dict[str, Any]:
    """
    Get weather forecast for a city using free wttr.in API
    
    Args:
        city: Name of the city
        days: Number of days (1-3, default 3)
    """
    try:
        # Use wttr.in forecast - also free!
        url = f"https://wttr.in/{city}?format=j1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        forecast_days = data["weather"][:min(days, 3)]  # wttr.in gives 3 days
        area = data["nearest_area"][0]
        
        forecasts = []
        for day in forecast_days:
            forecasts.append({
                "date": day["date"],
                "max_temp": f"{day['maxtempC']}°C ({day['maxtempF']}°F)",
                "min_temp": f"{day['mintempC']}°C ({day['mintempF']}°F)",
                "description": day["hourly"][4]["weatherDesc"][0]["value"],  # Mid-day weather
                "sunrise": day["astronomy"][0]["sunrise"],
                "sunset": day["astronomy"][0]["sunset"],
                "uv_index": day["uvIndex"]
            })
        
        return {
            "city": area["areaName"][0]["value"],
            "country": area["country"][0]["value"],
            "forecast": forecasts
        }
        
    except Exception as e:
        return {"error": f"Failed to get forecast: {str(e)}"}

def main():
    """Run the FastMCP server"""
    print("🌟 FastMCP Weather Server")
    print("=" * 30)
    
    print("🌤️  Using wttr.in - Free weather API (no signup needed!)")
    print("💡 No API keys required")
    print()
    
    print("🚀 Starting FastMCP server...")
    print("📡 Using streamable-http transport (latest)")
    print("🔍 For inspector: Use http://localhost:8000/mcp")
    print("💡 Press Ctrl+C to stop")
    print()
    
    # Use the new streamable-http transport instead of deprecated SSE
    mcp.run(transport="streamable-http", port=8000, host="0.0.0.0")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("💡 Try killing existing processes first:")
        print("   sudo fuser -k 8000/tcp")