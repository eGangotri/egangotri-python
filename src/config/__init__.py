"""Configuration module for the application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# MongoDB service configuration
MONGO_SERVICE_HOST = os.getenv('MONGO_SERVICE_HOST', 'localhost')
MONGO_SERVICE_PORT = os.getenv('MONGO_SERVICE_PORT', '8000')
MONGO_SERVICE_URL = f"http://{MONGO_SERVICE_HOST}:{MONGO_SERVICE_PORT}"

# API endpoints
API_ENDPOINTS = {
    'create_entry': f"{MONGO_SERVICE_URL}/imgToPdf/createImgToPdfEntry",
    'update_entry': f"{MONGO_SERVICE_URL}/imgToPdf/updateImgToPdfEntry"
}
