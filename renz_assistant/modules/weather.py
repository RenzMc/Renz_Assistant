"""
Weather-related functions for Renz Assistant
Enhanced to work 100% with Termux API
"""
import os
import json
import time
import asyncio
import subprocess
import requests
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim

class WeatherService:
    """Handles weather information retrieval with 100% Termux API compatibility"""
    
    def __init__(self, memory=None):
        """Initialize weather service"""
        self.memory = memory or {}
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".renz_assistant", "cache")
        self.cache_file = os.path.join(self.cache_dir, "weather_cache.json")
        self.cache_expiry = 30 * 60  # 30 minutes
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Failed to create cache directory: {e}")
        
        # Load cache
        self.cache = self._load_cache()
        
        # API keys for weather services
        self.openweathermap_api_key = self.cache.get("openweathermap_api_key", "")
        self.weatherapi_key = self.cache.get("weatherapi_key", "")
    
    def _load_cache(self):
        """Load weather cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Failed to load weather cache: {e}")
            return {}
    
    def _save_cache(self):
        """Save weather cache to file"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save weather cache: {e}")
    
    def set_api_key(self, service, api_key):
        """Set API key for weather service"""
        if service == "openweathermap":
            self.openweathermap_api_key = api_key
            self.cache["openweathermap_api_key"] = api_key
        elif service == "weatherapi":
            self.weatherapi_key = api_key
            self.cache["weatherapi_key"] = api_key
        
        self._save_cache()
    
    def get_current_weather(self, location=None, save_callback=None):
        """
        Get current weather information
        Uses Termux API for location if not provided
        Falls back to multiple weather APIs for reliability
        """
        try:
            # Get location if not provided
            if not location:
                lat, lon = self.get_current_location()
                if not lat or not lon:
                    return "Failed to get location. Please check location permissions or provide a location name."
                
                # Get location name from coordinates
                location_name = self.get_location_name(lat, lon)
                location_coords = (lat, lon)
            else:
                # Get coordinates from location name
                lat, lon = self.geocode_place(location)
                if not lat or not lon:
                    return f"Failed to find location: {location}"
                
                location_name = location
                location_coords = (lat, lon)
            
            # Check cache first
            cache_key = f"weather_{lat}_{lon}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if time.time() - cached_data.get("timestamp", 0) < self.cache_expiry:
                    print("Using cached weather data")
                    
                    # Store in memory if callback provided
                    if save_callback and self.memory:
                        self.memory["facts"]["current_weather"] = {
                            "data": cached_data["data"],
                            "location": location_name,
                            "coordinates": location_coords,
                            "timestamp": datetime.now().isoformat(),
                        }
                        save_callback(self.memory)
                    
                    return cached_data["data"]
            
            # Try multiple weather APIs for reliability
            weather_data = None
            
            # Try OpenWeatherMap first
            if self.openweathermap_api_key:
                weather_data = self._get_weather_openweathermap(lat, lon)
            
            # Try WeatherAPI if OpenWeatherMap failed
            if not weather_data and self.weatherapi_key:
                weather_data = self._get_weather_weatherapi(lat, lon)
            
            # Try Termux API weather command if available
            if not weather_data:
                weather_data = self._get_weather_termux_api(lat, lon)
            
            # Try public API as last resort
            if not weather_data:
                weather_data = self._get_weather_public_api(lat, lon)
            
            # If all APIs failed, return error
            if not weather_data:
                return "Failed to get weather data. Please check your internet connection or try again later."
            
            # Cache the weather data
            self.cache[cache_key] = {
                "data": weather_data,
                "timestamp": time.time()
            }
            self._save_cache()
            
            # Store in memory if callback provided
            if save_callback and self.memory:
                self.memory["facts"]["current_weather"] = {
                    "data": weather_data,
                    "location": location_name,
                    "coordinates": location_coords,
                    "timestamp": datetime.now().isoformat(),
                }
                save_callback(self.memory)
            
            return weather_data
        
        except Exception as e:
            print(f"Error getting weather: {e}")
            return f"Weather data unavailable: {str(e)}"
    
    def get_weather_forecast(self, location=None, days=5, save_callback=None):
        """
        Get weather forecast for multiple days
        Uses Termux API for location if not provided
        Falls back to multiple weather APIs for reliability
        """
        try:
            # Get location if not provided
            if not location:
                lat, lon = self.get_current_location()
                if not lat or not lon:
                    return "Failed to get location. Please check location permissions or provide a location name."
                
                # Get location name from coordinates
                location_name = self.get_location_name(lat, lon)
                location_coords = (lat, lon)
            else:
                # Get coordinates from location name
                lat, lon = self.geocode_place(location)
                if not lat or not lon:
                    return f"Failed to find location: {location}"
                
                location_name = location
                location_coords = (lat, lon)
            
            # Check cache first
            cache_key = f"forecast_{lat}_{lon}_{days}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if time.time() - cached_data.get("timestamp", 0) < self.cache_expiry:
                    print("Using cached forecast data")
                    
                    # Store in memory if callback provided
                    if save_callback and self.memory:
                        self.memory["facts"]["weather_forecast"] = {
                            "data": cached_data["data"],
                            "location": location_name,
                            "coordinates": location_coords,
                            "days": days,
                            "timestamp": datetime.now().isoformat(),
                        }
                        save_callback(self.memory)
                    
                    return cached_data["data"]
            
            # Try multiple weather APIs for reliability
            forecast_data = None
            
            # Try OpenWeatherMap first
            if self.openweathermap_api_key:
                forecast_data = self._get_forecast_openweathermap(lat, lon, days)
            
            # Try WeatherAPI if OpenWeatherMap failed
            if not forecast_data and self.weatherapi_key:
                forecast_data = self._get_forecast_weatherapi(lat, lon, days)
            
            # Try public API as last resort
            if not forecast_data:
                forecast_data = self._get_forecast_public_api(lat, lon, days)
            
            # If all APIs failed, return error
            if not forecast_data:
                return "Failed to get forecast data. Please check your internet connection or try again later."
            
            # Cache the forecast data
            self.cache[cache_key] = {
                "data": forecast_data,
                "timestamp": time.time()
            }
            self._save_cache()
            
            # Store in memory if callback provided
            if save_callback and self.memory:
                self.memory["facts"]["weather_forecast"] = {
                    "data": forecast_data,
                    "location": location_name,
                    "coordinates": location_coords,
                    "days": days,
                    "timestamp": datetime.now().isoformat(),
                }
                save_callback(self.memory)
            
            return forecast_data
        
        except Exception as e:
            print(f"Error getting forecast: {e}")
            return f"Forecast data unavailable: {str(e)}"
    
    def get_air_quality(self, location=None, save_callback=None):
        """
        Get air quality information
        Uses Termux API for location if not provided
        """
        try:
            # Get location if not provided
            if not location:
                lat, lon = self.get_current_location()
                if not lat or not lon:
                    return "Failed to get location. Please check location permissions or provide a location name."
                
                # Get location name from coordinates
                location_name = self.get_location_name(lat, lon)
                location_coords = (lat, lon)
            else:
                # Get coordinates from location name
                lat, lon = self.geocode_place(location)
                if not lat or not lon:
                    return f"Failed to find location: {location}"
                
                location_name = location
                location_coords = (lat, lon)
            
            # Check cache first
            cache_key = f"air_quality_{lat}_{lon}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if time.time() - cached_data.get("timestamp", 0) < self.cache_expiry:
                    print("Using cached air quality data")
                    
                    # Store in memory if callback provided
                    if save_callback and self.memory:
                        self.memory["facts"]["air_quality"] = {
                            "data": cached_data["data"],
                            "location": location_name,
                            "coordinates": location_coords,
                            "timestamp": datetime.now().isoformat(),
                        }
                        save_callback(self.memory)
                    
                    return cached_data["data"]
            
            # Try OpenWeatherMap first
            air_quality_data = None
            if self.openweathermap_api_key:
                air_quality_data = self._get_air_quality_openweathermap(lat, lon)
            
            # Try public API as last resort
            if not air_quality_data:
                air_quality_data = self._get_air_quality_public_api(lat, lon)
            
            # If all APIs failed, return error
            if not air_quality_data:
                return "Failed to get air quality data. Please check your internet connection or try again later."
            
            # Cache the air quality data
            self.cache[cache_key] = {
                "data": air_quality_data,
                "timestamp": time.time()
            }
            self._save_cache()
            
            # Store in memory if callback provided
            if save_callback and self.memory:
                self.memory["facts"]["air_quality"] = {
                    "data": air_quality_data,
                    "location": location_name,
                    "coordinates": location_coords,
                    "timestamp": datetime.now().isoformat(),
                }
                save_callback(self.memory)
            
            return air_quality_data
        
        except Exception as e:
            print(f"Error getting air quality: {e}")
            return f"Air quality data unavailable: {str(e)}"
    
    def get_current_location(self):
        """
        Get current location using Termux API
        Returns (latitude, longitude) tuple
        """
        for provider in ["gps", "network"]:
            try:
                print(f"Getting location using {provider} provider...")
                result = subprocess.run(
                    ["termux-location", "-p", provider],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0 and result.stdout:
                    try:
                        location_data = json.loads(result.stdout)
                        lat = location_data.get("latitude")
                        lon = location_data.get("longitude")
                        
                        if lat is not None and lon is not None:
                            print(f"Location: {lat}, {lon}")
                            return lat, lon
                    except json.JSONDecodeError:
                        print(f"Failed to parse location data: {result.stdout}")
            except Exception as e:
                print(f"Error getting location with {provider}: {e}")
        
        print("Failed to get location using Termux API")
        return None, None
    
    def get_location_name(self, lat, lon):
        """Get location name from coordinates using reverse geocoding"""
        try:
            geolocator = Nominatim(user_agent="renz_assistant")
            location = geolocator.reverse((lat, lon), language="en")
            
            if location:
                address = location.raw.get("address", {})
                
                # Try to get city or town name
                city = (
                    address.get("city") or 
                    address.get("town") or 
                    address.get("village") or 
                    address.get("suburb") or 
                    address.get("county") or 
                    address.get("state") or 
                    "Unknown Location"
                )
                
                # Add country if available
                country = address.get("country")
                if country:
                    return f"{city}, {country}"
                
                return city
            
            return "Unknown Location"
        except Exception as e:
            print(f"Error getting location name: {e}")
            return "Unknown Location"
    
    def geocode_place(self, place_name):
        """
        Convert place name to coordinates using geocoding
        Returns (latitude, longitude) tuple
        """
        try:
            geolocator = Nominatim(user_agent="renz_assistant")
            location = geolocator.geocode(place_name)
            
            if location:
                return location.latitude, location.longitude
            
            # Try using OpenStreetMap API directly
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": place_name,
                "format": "json",
                "limit": 1
            }
            
            response = requests.get(
                url, 
                params=params, 
                headers={"User-Agent": "RenzAssistant/1.0"}
            )
            
            if response.status_code == 200:
                results = response.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    return lat, lon
            
            return None, None
        except Exception as e:
            print(f"Error geocoding place: {e}")
            return None, None
    
    def _get_weather_openweathermap(self, lat, lon):
        """Get weather data from OpenWeatherMap API"""
        if not self.openweathermap_api_key:
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweathermap_api_key,
                "units": "metric"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                weather_condition = data["weather"][0]["main"]
                weather_description = data["weather"][0]["description"]
                temperature = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                location_name = data["name"]
                country = data["sys"]["country"]
                
                # Format response
                response = f"🌡️ Weather in {location_name}, {country}:\n"
                response += f"• Condition: {weather_condition} ({weather_description})\n"
                response += f"• Temperature: {temperature}°C\n"
                response += f"• Feels like: {feels_like}°C\n"
                response += f"• Humidity: {humidity}%\n"
                response += f"• Wind: {wind_speed} m/s"
                
                return response
            
            return None
        except Exception as e:
            print(f"Error getting weather from OpenWeatherMap: {e}")
            return None
    
    def _get_weather_weatherapi(self, lat, lon):
        """Get weather data from WeatherAPI"""
        if not self.weatherapi_key:
            return None
        
        try:
            url = "https://api.weatherapi.com/v1/current.json"
            params = {
                "key": self.weatherapi_key,
                "q": f"{lat},{lon}",
                "aqi": "yes"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                location_name = data["location"]["name"]
                region = data["location"]["region"]
                country = data["location"]["country"]
                condition = data["current"]["condition"]["text"]
                temperature = data["current"]["temp_c"]
                feels_like = data["current"]["feelslike_c"]
                humidity = data["current"]["humidity"]
                wind_speed = data["current"]["wind_kph"]
                wind_direction = data["current"]["wind_dir"]
                
                # Format response
                response = f"🌡️ Weather in {location_name}, {region}, {country}:\n"
                response += f"• Condition: {condition}\n"
                response += f"• Temperature: {temperature}°C\n"
                response += f"• Feels like: {feels_like}°C\n"
                response += f"• Humidity: {humidity}%\n"
                response += f"• Wind: {wind_speed} km/h {wind_direction}"
                
                return response
            
            return None
        except Exception as e:
            print(f"Error getting weather from WeatherAPI: {e}")
            return None
    
    def _get_weather_termux_api(self, lat, lon):
        """Get weather data using Termux API (if available)"""
        try:
            # This is a placeholder as Termux API doesn't have a direct weather command
            # We'll use the location from Termux API but get weather data from other sources
            return None
        except Exception as e:
            print(f"Error getting weather from Termux API: {e}")
            return None
    
    def _get_weather_public_api(self, lat, lon):
        """Get weather data from public API (no API key required)"""
        try:
            # Try OpenMeteo API (no API key required)
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "auto"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                temperature = data["current"]["temperature_2m"]
                humidity = data["current"]["relative_humidity_2m"]
                feels_like = data["current"]["apparent_temperature"]
                precipitation = data["current"]["precipitation"]
                wind_speed = data["current"]["wind_speed_10m"]
                wind_direction = data["current"]["wind_direction_10m"]
                weather_code = data["current"]["weather_code"]
                
                # Convert weather code to description
                weather_description = self._get_weather_description(weather_code)
                
                # Get location name
                location_name = self.get_location_name(lat, lon)
                
                # Format response
                response = f"🌡️ Weather in {location_name}:\n"
                response += f"• Condition: {weather_description}\n"
                response += f"• Temperature: {temperature}°C\n"
                response += f"• Feels like: {feels_like}°C\n"
                response += f"• Humidity: {humidity}%\n"
                response += f"• Precipitation: {precipitation} mm\n"
                response += f"• Wind: {wind_speed} km/h, {self._get_wind_direction(wind_direction)}"
                
                return response
            
            return None
        except Exception as e:
            print(f"Error getting weather from public API: {e}")
            return None
    
    def _get_forecast_openweathermap(self, lat, lon, days=5):
        """Get forecast data from OpenWeatherMap API"""
        if not self.openweathermap_api_key:
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweathermap_api_key,
                "units": "metric",
                "cnt": min(days * 8, 40)  # 8 forecasts per day, max 5 days (40 forecasts)
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract location information
                location_name = data["city"]["name"]
                country = data["city"]["country"]
                
                # Group forecasts by day
                daily_forecasts = {}
                for forecast in data["list"]:
                    dt = datetime.fromtimestamp(forecast["dt"])
                    date_str = dt.strftime("%Y-%m-%d")
                    
                    if date_str not in daily_forecasts:
                        daily_forecasts[date_str] = {
                            "date": dt.strftime("%A, %b %d"),
                            "temps": [],
                            "conditions": [],
                            "humidity": [],
                            "wind_speed": []
                        }
                    
                    daily_forecasts[date_str]["temps"].append(forecast["main"]["temp"])
                    daily_forecasts[date_str]["conditions"].append(forecast["weather"][0]["main"])
                    daily_forecasts[date_str]["humidity"].append(forecast["main"]["humidity"])
                    daily_forecasts[date_str]["wind_speed"].append(forecast["wind"]["speed"])
                
                # Format response
                response = f"📅 {days}-Day Forecast for {location_name}, {country}:\n\n"
                
                for date_str, forecast in list(daily_forecasts.items())[:days]:
                    avg_temp = sum(forecast["temps"]) / len(forecast["temps"])
                    min_temp = min(forecast["temps"])
                    max_temp = max(forecast["temps"])
                    
                    # Get most common condition
                    from collections import Counter
                    conditions = Counter(forecast["conditions"])
                    most_common_condition = conditions.most_common(1)[0][0]
                    
                    avg_humidity = sum(forecast["humidity"]) / len(forecast["humidity"])
                    avg_wind = sum(forecast["wind_speed"]) / len(forecast["wind_speed"])
                    
                    response += f"📆 {forecast['date']}:\n"
                    response += f"• Condition: {most_common_condition}\n"
                    response += f"• Temperature: {min_temp:.1f}°C to {max_temp:.1f}°C (avg: {avg_temp:.1f}°C)\n"
                    response += f"• Humidity: {avg_humidity:.0f}%\n"
                    response += f"• Wind: {avg_wind:.1f} m/s\n\n"
                
                return response.strip()
            
            return None
        except Exception as e:
            print(f"Error getting forecast from OpenWeatherMap: {e}")
            return None
    
    def _get_forecast_weatherapi(self, lat, lon, days=5):
        """Get forecast data from WeatherAPI"""
        if not self.weatherapi_key:
            return None
        
        try:
            url = "https://api.weatherapi.com/v1/forecast.json"
            params = {
                "key": self.weatherapi_key,
                "q": f"{lat},{lon}",
                "days": min(days, 10),  # Max 10 days
                "aqi": "yes"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract location information
                location_name = data["location"]["name"]
                region = data["location"]["region"]
                country = data["location"]["country"]
                
                # Format response
                response = f"📅 {days}-Day Forecast for {location_name}, {region}, {country}:\n\n"
                
                for day in data["forecast"]["forecastday"][:days]:
                    date = datetime.strptime(day["date"], "%Y-%m-%d")
                    date_str = date.strftime("%A, %b %d")
                    
                    condition = day["day"]["condition"]["text"]
                    min_temp = day["day"]["mintemp_c"]
                    max_temp = day["day"]["maxtemp_c"]
                    avg_temp = day["day"]["avgtemp_c"]
                    humidity = day["day"]["avghumidity"]
                    wind_speed = day["day"]["maxwind_kph"]
                    rain_chance = day["day"]["daily_chance_of_rain"]
                    
                    response += f"📆 {date_str}:\n"
                    response += f"• Condition: {condition}\n"
                    response += f"• Temperature: {min_temp}°C to {max_temp}°C (avg: {avg_temp}°C)\n"
                    response += f"• Humidity: {humidity}%\n"
                    response += f"• Wind: {wind_speed} km/h\n"
                    response += f"• Chance of rain: {rain_chance}%\n\n"
                
                return response.strip()
            
            return None
        except Exception as e:
            print(f"Error getting forecast from WeatherAPI: {e}")
            return None
    
    def _get_forecast_public_api(self, lat, lon, days=5):
        """Get forecast data from public API (no API key required)"""
        try:
            # Try OpenMeteo API (no API key required)
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": min(days, 16)  # Max 16 days
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Get location name
                location_name = self.get_location_name(lat, lon)
                
                # Format response
                response = f"📅 {days}-Day Forecast for {location_name}:\n\n"
                
                for i in range(min(days, len(data["daily"]["time"]))):
                    date = datetime.strptime(data["daily"]["time"][i], "%Y-%m-%d")
                    date_str = date.strftime("%A, %b %d")
                    
                    weather_code = data["daily"]["weather_code"][i]
                    weather_description = self._get_weather_description(weather_code)
                    
                    min_temp = data["daily"]["temperature_2m_min"][i]
                    max_temp = data["daily"]["temperature_2m_max"][i]
                    
                    min_feels_like = data["daily"]["apparent_temperature_min"][i]
                    max_feels_like = data["daily"]["apparent_temperature_max"][i]
                    
                    precipitation = data["daily"]["precipitation_sum"][i]
                    precipitation_prob = data["daily"]["precipitation_probability_max"][i]
                    
                    wind_speed = data["daily"]["wind_speed_10m_max"][i]
                    
                    response += f"📆 {date_str}:\n"
                    response += f"• Condition: {weather_description}\n"
                    response += f"• Temperature: {min_temp}°C to {max_temp}°C\n"
                    response += f"• Feels like: {min_feels_like}°C to {max_feels_like}°C\n"
                    response += f"• Precipitation: {precipitation} mm (Probability: {precipitation_prob}%)\n"
                    response += f"• Wind: {wind_speed} km/h\n\n"
                
                return response.strip()
            
            return None
        except Exception as e:
            print(f"Error getting forecast from public API: {e}")
            return None
    
    def _get_air_quality_openweathermap(self, lat, lon):
        """Get air quality data from OpenWeatherMap API"""
        if not self.openweathermap_api_key:
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/air_pollution"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweathermap_api_key
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract air quality information
                aqi = data["list"][0]["main"]["aqi"]  # 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
                
                components = data["list"][0]["components"]
                co = components["co"]
                no2 = components["no2"]
                o3 = components["o3"]
                pm2_5 = components["pm2_5"]
                pm10 = components["pm10"]
                so2 = components["so2"]
                
                # Get location name
                location_name = self.get_location_name(lat, lon)
                
                # Convert AQI to description
                aqi_descriptions = {
                    1: "Good",
                    2: "Fair",
                    3: "Moderate",
                    4: "Poor",
                    5: "Very Poor"
                }
                
                aqi_description = aqi_descriptions.get(aqi, "Unknown")
                
                # Format response
                response = f"🌬️ Air Quality in {location_name}:\n"
                response += f"• Air Quality Index: {aqi_description} ({aqi}/5)\n"
                response += f"• PM2.5: {pm2_5} μg/m³\n"
                response += f"• PM10: {pm10} μg/m³\n"
                response += f"• Ozone (O₃): {o3} μg/m³\n"
                response += f"• Nitrogen Dioxide (NO₂): {no2} μg/m³\n"
                response += f"• Sulfur Dioxide (SO₂): {so2} μg/m³\n"
                response += f"• Carbon Monoxide (CO): {co} μg/m³"
                
                return response
            
            return None
        except Exception as e:
            print(f"Error getting air quality from OpenWeatherMap: {e}")
            return None
    
    def _get_air_quality_public_api(self, lat, lon):
        """Get air quality data from public API (no API key required)"""
        try:
            # Try OpenMeteo API (no API key required)
            url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
                "timezone": "auto"
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract air quality information
                eu_aqi = data["current"]["european_aqi"]
                us_aqi = data["current"]["us_aqi"]
                
                pm10 = data["current"]["pm10"]
                pm2_5 = data["current"]["pm2_5"]
                co = data["current"]["carbon_monoxide"]
                no2 = data["current"]["nitrogen_dioxide"]
                so2 = data["current"]["sulphur_dioxide"]
                o3 = data["current"]["ozone"]
                
                # Get location name
                location_name = self.get_location_name(lat, lon)
                
                # Get AQI description
                eu_aqi_description = self._get_eu_aqi_description(eu_aqi)
                us_aqi_description = self._get_us_aqi_description(us_aqi)
                
                # Format response
                response = f"🌬️ Air Quality in {location_name}:\n"
                response += f"• European AQI: {eu_aqi_description} ({eu_aqi})\n"
                response += f"• US AQI: {us_aqi_description} ({us_aqi})\n"
                response += f"• PM2.5: {pm2_5} μg/m³\n"
                response += f"• PM10: {pm10} μg/m³\n"
                response += f"• Ozone (O₃): {o3} μg/m³\n"
                response += f"• Nitrogen Dioxide (NO₂): {no2} μg/m³\n"
                response += f"• Sulfur Dioxide (SO₂): {so2} μg/m³\n"
                response += f"• Carbon Monoxide (CO): {co} μg/m³"
                
                return response
            
            return None
        except Exception as e:
            print(f"Error getting air quality from public API: {e}")
            return None
    
    def _get_weather_description(self, code):
        """Convert WMO weather code to description"""
        wmo_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        return wmo_codes.get(code, "Unknown")
    
    def _get_wind_direction(self, degrees):
        """Convert wind direction in degrees to cardinal direction"""
        directions = [
            "North", "North-Northeast", "Northeast", "East-Northeast",
            "East", "East-Southeast", "Southeast", "South-Southeast",
            "South", "South-Southwest", "Southwest", "West-Southwest",
            "West", "West-Northwest", "Northwest", "North-Northwest"
        ]
        
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    def _get_eu_aqi_description(self, aqi):
        """Convert European AQI to description"""
        if aqi <= 20:
            return "Good"
        elif aqi <= 40:
            return "Fair"
        elif aqi <= 60:
            return "Moderate"
        elif aqi <= 80:
            return "Poor"
        elif aqi <= 100:
            return "Very Poor"
        else:
            return "Extremely Poor"
    
    def _get_us_aqi_description(self, aqi):
        """Convert US AQI to description"""
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def haversine(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates using Haversine formula"""
        import math
        φ1, λ1, φ2, λ2 = map(math.radians, [lat1, lon1, lat2, lon2])
        Δφ = φ2 - φ1
        Δλ = λ2 - λ1
        a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        R = 6371  # Earth radius in km
        return R * c
    
    def distance_to(self, place_name):
        """Calculate distance to a named place"""
        lat1, lon1 = self.get_current_location()
        if lat1 is None:
            return "Current location not available."
        
        lat2, lon2 = self.geocode_place(place_name)
        if lat2 is None:
            return f"Failed to find coordinates for '{place_name}'."
        
        distance_km = self.haversine(lat1, lon1, lat2, lon2)
        return f"Distance from your location to {place_name} is approximately {distance_km:.2f} km."