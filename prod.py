import sys
import os

# Debug: Confirm module is loaded
print("Loading prod.py...")

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

# Debug: Confirm environment variables are loaded
print("Loading environment variables...")
load_dotenv()
print("Environment variables loaded.")

# Import shared definitions from common.py
print("Importing from common.py...")
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
print("Imported from common.py successfully.")

# Debug: Confirm Flask app creation
print("Creating Flask app instance...")
app = Flask(__name__)
print("Flask app instance created:", app)

logging.basicConfig(level=logging.INFO)

# Configure Swagger for OpenAPI 3.0.0
print("Configuring Swagger...")
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
print("Swagger configured successfully.")

# Load API keys from environment variables with fallbacks
print("Loading API keys from environment variables...")
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "aa8383339a96386447225767adc27e61")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
print(f"WEATHER_API_KEY: {'Set' if WEATHER_API_KEY else 'Not set'}")
print(f"OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not set'}")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is required in .env for production")
openai.api_key = OPENAI_API_KEY
print("API keys loaded and set for OpenAI.")

# Register endpoints
def register_endpoints():
    try:
        print("Attempting to import and register endpoints...")
        logger.info("Attempting to import and register endpoints...")
        from api_endpoints.exact_pour import exact_pour_calculations
        from api_endpoints.best_pour import best_pour_calculations
        from api_endpoints.roofing import roofing_calculations
        print(f"Imported blueprints: exact_pour={exact_pour_calculations}, best_pour={best_pour_calculations}, roofing={roofing_calculations}")
        logger.info(f"Imported blueprints: exact_pour={exact_pour_calculations}, best_pour={best_pour_calculations}, roofing={roofing_calculations}")
        app.register_blueprint(exact_pour_calculations, url_prefix='/api/calculate')
        app.register_blueprint(best_pour_calculations, url_prefix='/api/calculate')
        app.register_blueprint(roofing_calculations, url_prefix='/api/calculate')
        print("Endpoints registered successfully.")
        logger.info("Endpoints registered successfully")
        # Log registered routes for debugging
        for rule in app.url_map.iter_rules():
            print(f"Registered route: {rule} (methods: {rule.methods})")
            logger.info(f"Registered route: {rule} (methods: {rule.methods})")
    except ImportError as e:
        print(f"Failed to import endpoint modules: {str(e)}")
        logger.error(f"Failed to import endpoint modules: {str(e)}")
        raise
    except Exception as e:
        print(f"Failed to register endpoints: {str(e)}")
        logger.error(f"Failed to register endpoints: {str(e)}")
        raise

# Apply rate limiting
print("Applying rate limiting...")
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["100 per day"])
print("Rate limiting applied.")

# Register all endpoints (only once at module level)
print("Registering all endpoints...")
register_endpoints()
print("All endpoints registered.")

# Add a debug route to see all headers
@app.route('/api/debug', methods=['GET', 'POST'])
def debug_headers():
    """
    Debug endpoint to see all headers sent by RapidAPI
    """
    # Create a dictionary with all headers
    headers = dict(request.headers)
    
    # Create sanitized headers for logging (without sensitive info)
    sanitized_headers = {k: v for k, v in headers.items() if not any(
        sensitive in k.lower() for sensitive in ['key', 'token', 'auth']
    )}
    logger.info(f"DEBUG ENDPOINT: Received headers: {sanitized_headers}")
    
    # Create a response with all headers, request method, and path
    response = {
        "status": "success",
        "message": "Debug endpoint - displaying all headers",
        "timestamp": datetime.now().isoformat(),
        "headers": headers,
        "method": request.method,
        "path": request.path,
        "has_rapidapi_key": "X-RapidAPI-Key" in headers,
        "has_rapidapi_host": "X-RapidAPI-Host" in headers,
        "has_api_key": "X-API-Key" in headers,
        "has_authorization": "Authorization" in headers
    }
    
    return jsonify(response)

if __name__ == "__main__":
    print("Starting Flask app...")
    port = int(os.getenv("PORT"))  # Use PORT env var without fallback
    print(f"Running on port: {port}")
    app.run(debug=False, host="0.0.0.0", port=port)
    print("Flask app started.")