# api_endpoints/roofing.py
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from common import RoofingRequest, get_weather_data, find_work_windows, suggest_materials, cached_parse_response, require_api_key, logger
import pytz
import json
from datetime import datetime  # Use direct import so that datetime.strptime works

roofing_bp = Blueprint('roofing', __name__)

@roofing_bp.route("/roofing_weather", methods=["POST"])
@swag_from({
    "summary": "Get roofing weather recommendations",
    "description": "Provides weather suitability and work windows for roofing.",
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": RoofingRequest.model_json_schema()
            }
        }
    },
    "responses": {
        "200": {"description": "Success"},
        "400": {"description": "Invalid input"}
    }
})
@require_api_key
def roofing_weather():
    logger.info(f"Received roofing_weather request: {request.get_json()}")
    try:
        data = RoofingRequest(**request.get_json())
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400

    lat = data.latitude
    lon = data.longitude
    start_time = data.start_time
    tz = data.timezone
    tz_obj = pytz.timezone(tz)
    start_dt = tz_obj.localize(datetime.strptime(start_time, "%Y-%m-%d %H:%M"))

    try:
        weather_data = get_weather_data(lat, lon)
    except Exception as e:
        logger.error(f"Weather fetch error: {str(e)}")
        return jsonify({"error": "Weather data unavailable"}), 500

    work_windows = find_work_windows(weather_data, start_dt, tz_obj)
    material_suggestions = suggest_materials(weather_data, start_dt, tz_obj)

    response_data = {
        "coordinates": {"lat": lat, "lon": lon},
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M %Z"),
        "roofing_type": data.roofing_type,
        "weather_suitability": "Good to go",
        "risks": [],
        "weather_risk_timeline": [],
        "cost_impact": "Weather looks fine for roofing—no delays expected.",
        "recommended_work_windows": work_windows,
        "material_suggestions": material_suggestions
    }
    human_friendly_insight = cached_parse_response(response_data, "roofing_weather", tz)
    response = {
        **response_data,
        "human_friendly_insight": human_friendly_insight,
        "disclaimer": "These are general estimates for planning purposes only and not precise predictions."
    }
    logger.info(f"Generated response: {json.dumps(response, indent=2)}")
    return jsonify(response), 200

roofing_calculations = roofing_bp
