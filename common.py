# common.py
import os
import json
import logging
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Optional
from functools import wraps
from flask import request, jsonify
from pydantic import BaseModel, field_validator, model_validator
import openai

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for weather thresholds
WEATHER_THRESHOLD_TEMP_MIN = 5.0  # Celsius
WEATHER_THRESHOLD_TEMP_MAX = 35.0  # Celsius
WEATHER_THRESHOLD_HUMIDITY_MAX = 80  # Percentage
WEATHER_THRESHOLD_RAIN = 0.5  # mm/3h

# Load configuration
try:
    from config import API_KEY, WEATHER_API_KEY, OPENAI_API_KEY

    logger.info("Configuration loaded from config.py")
except ImportError:
    logger.warning("config.py not found, falling back to environment variables")
    API_KEY = os.getenv("API_KEY")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Valid API keys
VALID_API_KEYS = {API_KEY} if API_KEY else set()
logger.info(f"Valid API keys: {VALID_API_KEYS}")

# OpenAI client setup
openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=OPENAI_API_KEY)


# Pydantic models for request validation
class PourRequest(BaseModel):
    latitude: float
    longitude: float
    pour_time: str
    concrete_type: str = "Type I"
    custom_concrete: Optional[Dict[str, Any]] = None
    timezone: str

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        try:
            pytz.timezone(value)
            return value
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {value}")

    @model_validator(mode="after")
    def validate_pour_time_with_timezone(self):
        timezone = self.timezone
        try:
            tz = pytz.timezone(timezone)
            pour_dt = datetime.strptime(self.pour_time, "%Y-%m-%d %H:%M")
            pour_dt = tz.localize(pour_dt)
            current_dt = datetime.now(tz)
            if pour_dt < current_dt:
                raise ValueError("Pour time cannot be in the past")
            if (pour_dt - current_dt).days > 5:
                raise ValueError("Pour time is beyond 5-day forecast range")
            return self
        except ValueError as e:
            raise ValueError(f"Pour time validation failed: {str(e)}")


class BestPourRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    request_date: Optional[str] = None
    concrete_type: str = "Type I"
    custom_concrete: Optional[Dict[str, Any]] = None
    timezone: str

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value

    @field_validator("start_date", "end_date", "request_date")
    @classmethod
    def validate_date_format(cls, value):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
                return value
            except ValueError:
                raise ValueError("Date must be in format 'YYYY-MM-DD'")


class RoofingRequest(BaseModel):
    latitude: float
    longitude: float
    start_time: str
    timezone: str
    roofing_type: str = "Asphalt Shingles"
    custom_roofing: Optional[Dict[str, Any]] = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        try:
            pytz.timezone(value)
            return value
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {value}")

    @model_validator(mode="after")
    def validate_start_time_with_timezone(self):
        timezone = self.timezone
        try:
            tz = pytz.timezone(timezone)
            start_dt = datetime.strptime(self.start_time, "%Y-%m-%d %H:%M")
            start_dt = tz.localize(start_dt)
            current_dt = datetime.now(tz)
            if start_dt < current_dt:
                raise ValueError("Start time cannot be in the past")
            if (start_dt - current_dt).days > 5:
                raise ValueError("Start time is beyond 5-day forecast range")
            return self
        except ValueError as e:
            raise ValueError(f"Start time validation failed: {str(e)}")


# API key decorator (to be replaced)
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in VALID_API_KEYS:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)

    return decorated


# Validate API key from RapidAPI (X-API-Key header)
def validate_api_key():
    """
    Validates the API key from the request.
    Returns tuple of (is_valid, message, status_code)
    """
    # Log headers for debugging (excluding sensitive headers)
    headers_dict = dict(request.headers)
    sanitized_headers = {k: v for k, v in headers_dict.items() if not any(sensitive in k.lower() for sensitive in ['key', 'token', 'auth', 'secret'])}
    logger.info(f"Received request with headers: {sanitized_headers}")
    
    # Check if RapidAPI integration is enabled
    accept_rapidapi = os.getenv('ACCEPT_RAPIDAPI', 'false').lower() == 'true'
    
    # First check standard API key header
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key in VALID_API_KEYS:
        logger.info("Request authenticated via X-API-Key")
        return True, "Valid API key", 200
    
    # If RapidAPI is enabled, check for RapidAPI headers
    if accept_rapidapi:
        # Check for the RapidAPI host header to identify RapidAPI requests
        rapid_api_host = request.headers.get('X-RapidAPI-Host')
        
        # Only proceed with RapidAPI validation if the host header is present
        if rapid_api_host:
            # Check for the RapidAPI proxy secret which should be present in genuine RapidAPI requests
            rapid_api_proxy_secret = request.headers.get('X-RapidAPI-Proxy-Secret')
            rapid_api_user = request.headers.get('X-RapidAPI-User')
            
            if rapid_api_proxy_secret:
                logger.info(f"Request authenticated via RapidAPI proxy secret, host: {rapid_api_host}, user: {rapid_api_user}")
                return True, "Valid RapidAPI request", 200
            
            # As a fallback, check additional RapidAPI headers if proxy secret is missing
            if request.headers.get('X-RapidAPI-Subscription'):
                logger.info(f"Request authenticated via RapidAPI subscription, host: {rapid_api_host}, user: {rapid_api_user}")
                return True, "Valid RapidAPI request", 200
    
    # If we get here, authentication failed
    if not api_key:
        logger.warning("No X-API-Key header provided and not a valid RapidAPI request")
        return False, "Valid API key or RapidAPI authentication required", 401
    else:
        logger.warning(f"Invalid API key provided: {api_key}")
        return False, "Invalid API key", 403


# Mock weather data fetch (replace with actual API call in production)
def get_weather_data(lat: float, lon: float) -> Dict[str, Any]:
    return {
        "list": [
            {
                "dt": int(datetime.now().timestamp()) + i * 3600,
                "main": {"temp": 293.15, "humidity": 50},
                "rain": {"3h": 0}
            } for i in range(8)
        ]
    }


# Placeholder for concrete curing calculation
def calculate_concrete_curing(weather_data: Dict[str, Any], pour_time: str, concrete_type: str,
                              custom_concrete: Optional[Dict[str, Any]] = None):
    base_hours = custom_concrete.get("base_curing_hours", 24) if custom_concrete else 24
    min_time = base_hours - 2
    max_time = base_hours + 2
    pour_dt = datetime.strptime(pour_time, "%Y-%m-%d %H:%M")
    end_time = (pour_dt + timedelta(hours=max_time)).strftime("%Y-%m-%d %H:%M")
    reasons = ["Weather looks good for curing"]
    summary = f"Typically cures in about {min_time}–{max_time} hours depending on weather"
    return min_time, max_time, end_time, reasons, summary


# Placeholder for paint drying calculation
def calculate_paint_drying(weather_data: Dict[str, Any], pour_time: str):
    min_time = 2
    max_time = 6
    pour_dt = datetime.strptime(pour_time, "%Y-%m-%d %H:%M")
    end_time = (pour_dt + timedelta(hours=max_time)).strftime("%Y-%m-%d %H:%M")
    reasons = ["Weather looks good for drying"]
    summary = f"Typically dries in about {min_time}–{max_time} hours depending on weather"
    return min_time, max_time, end_time, reasons, summary


# Function to find best pouring times for /best_pour endpoint
def find_best_pouring_times(weather_data: Dict[str, Any], start_date: str, end_date: str, concrete_type: str,
                            tz_obj: pytz.timezone) -> List[Dict[str, str]]:
    start_dt = tz_obj.localize(datetime.strptime(start_date + " 00:00", "%Y-%m-%d %H:%M"))
    end_dt = tz_obj.localize(datetime.strptime(end_date + " 23:59", "%Y-%m-%d %H:%M"))
    pour_times = []

    current_dt = start_dt
    while current_dt <= end_dt:
        pour_time = current_dt.strftime("%Y-%m-%d 15:53")
        min_time, max_time, end_time, reasons, _ = calculate_concrete_curing(weather_data, pour_time, concrete_type)
        pour_times.append({
            "pour_time": pour_time,
            "curing_time": f"{min_time}–{max_time} hours",
            "estimated_end_time": end_time,
            "why_this_time": reasons
        })
        current_dt += timedelta(days=1)

    return pour_times


# Placeholder for finding work windows
def find_work_windows(weather_data: Dict[str, Any], start_dt: datetime, tz_obj: pytz.timezone) -> List[Dict[str, str]]:
    windows = []
    start = start_dt
    for i in range(3):
        window_start = (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M %Z")
        window_end = (start + timedelta(hours=i + 3)).strftime("%Y-%m-%d %H:%M %Z")
        windows.append({
            "start": window_start,
            "end": window_end,
            "note": "Clear weather, good for work"
        })
    return windows


# Placeholder for material suggestions
def suggest_materials(weather_data: Dict[str, Any], start_dt: datetime, tz_obj: pytz.timezone,
                      concrete_type: str = "Type I") -> List[str]:
    return ["Current material looks fine for the weather."]


# Placeholder for response parsing with OpenAI
def cached_parse_response(response_data: Dict[str, Any], endpoint_type: str, tz: str) -> str:
    # Create specialized prompts based on endpoint type
    if endpoint_type == "exact_pour":
        system_message = """You are Jim, a 30-year veteran concrete contractor who gives straight-talking, practical advice.
        Always refer to locations by city/region name, NEVER mention coordinates in your response.
        Speak directly to the contractor as if you're having a conversation at a job site.
        Use natural conversational language. Avoid technical jargon unless essential.
        Never use phrases like "human-friendly insight", "based on the provided data", or similar AI-like language."""
        
        prompt = f"""The customer needs advice about a concrete pour scheduled for the coordinates in this data.
        
        Your response should:
        - Convert the coordinates to a city/region name (don't mention coordinates in your response)
        - Talk about the pour timing and expected curing time in practical terms
        - Mention relevant weather factors that might affect the quality of the work
        - Give practical advice as if you're talking to another contractor at a job site
        - Suggest what other construction tasks could be scheduled after curing completes
        
        Data: {json.dumps(response_data)} in timezone {tz}"""
    
    elif endpoint_type == "best_pour":
        system_message = """You are Mike, a construction foreman with 25 years of experience scheduling concrete jobs.
        Always refer to locations by city/region name, NEVER mention coordinates in your response.
        Speak as if you're giving advice to a fellow contractor planning their week.
        Use natural conversational language with a helpful, practical tone.
        Never use phrases like "human-friendly insight", "based on the provided data", or similar AI-like language."""
        
        prompt = f"""The customer needs to know the best day to schedule a concrete pour at the coordinates in this data.
        
        Your response should:
        - Convert the coordinates to a city/region name (don't mention coordinates in your response)
        - Give clear advice about which day/time is best for pouring
        - Explain in practical terms why that time is better than alternatives
        - Include any weather concerns they should know about
        - Speak like you would to a colleague at a construction site
        
        Data: {json.dumps(response_data)} in timezone {tz}"""
    
    elif endpoint_type == "roofing_weather":
        system_message = """You are Dave, a roofing contractor with decades of experience working with various roofing materials.
        Always refer to locations by city/region name, NEVER mention coordinates in your response.
        Speak as if you're giving advice to a homeowner or contractor at a building supply store.
        Use natural conversational language with a helpful, practical tone.
        Never use phrases like "human-friendly insight", "based on the provided data", or similar AI-like language."""
        
        prompt = f"""The customer needs to know if the weather is good for installing {response_data.get('roofing_type', 'roofing')} at the coordinates in this data.
        
        Your response should:
        - Convert the coordinates to a city/region name (don't mention coordinates in your response)
        - Speak clearly about whether the weather looks good or bad for the roofing job
        - Mention any specific weather factors that might affect installation quality
        - Give practical recommendations about timing the work
        - Sound like natural advice you'd give to someone at a job site
        
        Data: {json.dumps(response_data)} in timezone {tz}"""
    
    else:
        # Default prompt for any other endpoint types
        system_message = "You are an experienced construction professional providing practical, direct advice."
        prompt = f"Give straightforward, helpful feedback about this construction data. Don't mention coordinates directly, use city/region names instead: {json.dumps(response_data)} in timezone {tz}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "Simplified response for testing."