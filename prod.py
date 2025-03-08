import sys
import os

# Set up sys.path so that the project root is included
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
print("Current sys.path (after cleanup):", sys.path)

from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import importlib
import logging
import pytz
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import openai
from functools import wraps

# Load environment variables
load_dotenv()

# Import shared definitions from common.py
from common import (
    PourRequest,
    get_weather_data,
    calculate_concrete_curing,
    calculate_paint_drying,
    find_best_pouring_times,
    cached_parse_response,
    require_api_key,
    logger,
    validate_api_key
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configure Swagger for OpenAPI 3.0.0
app.config['SWAGGER'] = {
    'uiversion': 3,
    'openapi': '3.0.0',
    'specs': [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ]
}
swagger_template = {
    "openapi": "3.0.0",
    "info": {
        "title": "Construction Weather Predictor",
        "description": "Predict concrete curing, paint drying, and roofing suitability based on weather forecasts, with AI-generated, professional insights.",
        "version": "1.0.0"
    },
    "externalDocs": {
        "description": "Full docs on RapidAPI",
        "url": "https://rapidapi.com/your-api"
    },
    "components": {}
}
swagger = Swagger(app, template=swagger_template)

# Load API keys from environment variables with fallbacks
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "aa8383339a96386447225767adc27e61")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is required in .env for production")
openai.api_key = OPENAI_API_KEY

# Register endpoints
def register_endpoints():
    try:
        logger.info("Attempting to import and register endpoints...")
        from api_endpoints.exact_pour import exact_pour_calculations
        from api_endpoints.best_pour import best_pour_calculations
        from api_endpoints.roofing import roofing_calculations
        logger.info(f"Imported blueprints: exact_pour={exact_pour_calculations}, best_pour={best_pour_calculations}, roofing={roofing_calculations}")
        app.register_blueprint(exact_pour_calculations, url_prefix='/api/calculate')
        app.register_blueprint(best_pour_calculations, url_prefix='/api/calculate')
        app.register_blueprint(roofing_calculations, url_prefix='/api/calculate')
        logger.info("Endpoints registered successfully")
        # Log registered routes for debugging
        for rule in app.url_map.iter_rules():
            logger.info(f"Registered route: {rule} (methods: {rule.methods})")
    except ImportError as e:
        logger.error(f"Failed to import endpoint modules: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to register endpoints: {str(e)}")
        raise

# Apply rate limiting
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["100 per day"])

# Register all endpoints (only once at module level)
register_endpoints()

if __name__ == "__main__":
    port = int(os.getenv("PORT"))  # Use PORT env var without fallback
    app.run(debug=False, host="0.0.0.0", port=port)