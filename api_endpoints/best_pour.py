# api_endpoints/best_pour.py
from flask import Blueprint, request, jsonify
from flasgger import swag_from
import pytz
from datetime import datetime
from pydantic import ValidationError
from common import (
    BestPourRequest,
    get_weather_data,
    find_best_pouring_times,
    find_work_windows,
    suggest_materials,
    cached_parse_response,
    logger,
    WEATHER_THRESHOLD_TEMP_MIN,
    WEATHER_THRESHOLD_TEMP_MAX,
    WEATHER_THRESHOLD_HUMIDITY_MAX,
    WEATHER_THRESHOLD_RAIN,
    validate_api_key
)
import json

best_pour_bp = Blueprint('best_pour', __name__)

@best_pour_bp.route("/best_pour", methods=["POST"])
@swag_from({
    "summary": "Find the best pouring times within a date range",
    "description": "Returns suggested pour times with weather risk timeline.",
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "example": 38.5816},
                        "longitude": {"type": "number", "example": -121.4944},
                        "start_date": {"type": "string", "example": "2025-03-07"},
                        "end_date": {"type": "string", "example": "2025-03-09"},
                        "concrete_type": {"type": "string", "default": "Type I"},
                        "timezone": {"type": "string", "example": "America/Los_Angeles"}
                    },
                    "required": ["latitude", "longitude", "start_date", "end_date"]
                }
            }
        }
    },
    "responses": {
        "200": {"description": "Successful prediction"},
        "400": {"description": "Invalid input"}
    }
})
def best_pour_calculations():
    # Validate API key using the new function from common.py
    is_valid, message, status_code = validate_api_key()
    if not is_valid:
        return jsonify({"error": message}), status_code

    logger.info(f"Received best_pour request: {request.get_json()}")
    try:
        data = BestPourRequest(**request.get_json())
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Invalid JSON format: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400

    lat = data.latitude
    lon = data.longitude
    start_date = data.start_date
    end_date = data.end_date
    concrete_type = data.concrete_type
    custom_concrete = data.custom_concrete
    tz = data.timezone
    tz_obj = pytz.timezone(tz)

    try:
        weather_data = get_weather_data(lat, lon)
    except Exception as e:
        logger.error(f"Weather fetch error: {str(e)}")
        return jsonify({"error": "Weather data unavailable"}), 500

    if data.request_date:
        start_dt = tz_obj.localize(datetime.strptime(data.request_date, "%Y-%m-%d"))
    else:
        start_dt = datetime.now(tz_obj)

    # Fix the call to find_best_pouring_times
    optimal_windows = find_best_pouring_times(weather_data, start_date, end_date, concrete_type, tz_obj)

    weather_risks = []
    for forecast in weather_data["list"][:8]:
        forecast_dt = datetime.fromtimestamp(forecast["dt"], tz_obj)
        if forecast_dt < start_dt:
            continue
        temp = forecast["main"]["temp"] - 273.15
        humidity = forecast["main"]["humidity"]
        rain = forecast.get("rain", {}).get("3h", 0)
        risk_score = 0
        details = []
        if rain > WEATHER_THRESHOLD_RAIN:
            risk_score += 50
            details.append(f"Rain ({rain} mm)")
        if temp < WEATHER_THRESHOLD_TEMP_MIN:
            risk_score += 30
            details.append(f"Cold ({temp:.1f}°C)")
        elif temp > WEATHER_THRESHOLD_TEMP_MAX:
            risk_score += 30
            details.append(f"Hot ({temp:.1f}°C)")
        if humidity > WEATHER_THRESHOLD_HUMIDITY_MAX:
            risk_score += 20
            details.append(f"High humidity ({humidity}%)")
        risk = "High" if risk_score > 50 else "Medium" if risk_score > 20 else "Low"
        weather_risks.append({
            "time": forecast_dt.strftime("%Y-%m-%d %H:%M %Z"),
            "risk": risk,
            "risk_score": min(risk_score, 100),
            "details": details if details else ["Safe conditions"]
        })

    work_windows = find_work_windows(weather_data, start_dt, tz_obj)
    material_suggestions = suggest_materials(weather_data, start_dt, tz_obj, concrete_type=concrete_type)

    response_data = {
        "coordinates": {"lat": lat, "lon": lon},
        "suggested_pour_times": optimal_windows,
        "weather_risk_timeline": weather_risks,
        "recommended_work_windows": work_windows,
        "material_suggestions": material_suggestions
    }
    human_friendly_insight = cached_parse_response(response_data, "best_pour", tz)
    response = {
        **response_data,
        "human_friendly_insight": human_friendly_insight,
        "disclaimer": "These are general estimates for planning purposes only and not precise predictions."
    }
    logger.info(f"Generated response for best pour: {json.dumps(response, indent=2)}")
    return jsonify(response), 200

best_pour_calculations = best_pour_bp