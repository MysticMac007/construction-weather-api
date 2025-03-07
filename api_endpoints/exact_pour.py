# api_endpoints/exact_pour.py
from flask import Blueprint, request, jsonify
from flasgger import swag_from
import pytz
import json
from common import PourRequest, get_weather_data, calculate_concrete_curing, calculate_paint_drying, cached_parse_response, require_api_key, logger

exact_pour_bp = Blueprint('exact_pour', __name__)

@exact_pour_bp.route("/exact_pour", methods=["POST"])
@swag_from({
    "summary": "Get exact pour calculations",
    "description": "Provides curing and drying times for a specific pour time.",
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": PourRequest.model_json_schema()
            }
        }
    },
    "responses": {"200": {"description": "Success"}, "400": {"description": "Invalid input"}}
})
@require_api_key
def exact_pour():
    logger.info(f"Received exact_pour request: {request.get_json()}")
    try:
        data = PourRequest(**request.get_json())
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400

    lat = data.latitude
    lon = data.longitude
    pour_time = data.pour_time
    concrete_type = data.concrete_type
    custom_concrete = data.custom_concrete
    tz = data.timezone
    tz_obj = pytz.timezone(tz)

    try:
        weather_data = get_weather_data(lat, lon)
    except Exception as e:
        logger.error(f"Weather fetch error: {str(e)}")
        return jsonify({"error": "Weather data unavailable"}), 500

    min_curing, max_curing, end_curing, reasons_curing, summary_curing = calculate_concrete_curing(weather_data, pour_time, concrete_type, custom_concrete)
    min_drying, max_drying, end_drying, reasons_drying, summary_drying = calculate_paint_drying(weather_data, pour_time)

    response_data = {
        "coordinates": {"lat": lat, "lon": lon},
        "pour_time": pour_time,
        "concrete_curing": {
            "min_time": min_curing,
            "max_time": max_curing,
            "end_time": end_curing,
            "reasons": reasons_curing,
            "summary": summary_curing
        },
        "paint_drying": {
            "min_time": min_drying,
            "max_time": max_drying,
            "end_time": end_drying,
            "reasons": reasons_drying,
            "summary": summary_drying
        }
    }
    human_friendly_insight = cached_parse_response(response_data, "exact_pour", tz)
    response = {
        **response_data,
        "human_friendly_insight": human_friendly_insight,
        "disclaimer": "These are general estimates for planning purposes only and not precise predictions."
    }
    logger.info(f"Generated response: {json.dumps(response, indent=2)}")
    return jsonify(response), 200

exact_pour_calculations = exact_pour_bp