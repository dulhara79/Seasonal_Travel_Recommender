import os
from dotenv import load_dotenv

# load_dotenv(dotenv_path="C:/Users/dulha/GitHub/Seasonal_Travel_Recommender/server/.env")

# load .env located at server/.env (relative, robust across machines)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))   # server/
DOTENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=DOTENV_PATH)

# Database
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB')

# CORS
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS')

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# JWT
# JWT_SECRET = os.getenv('JWT_SECRET', 'f4buctOtskxFmHeYIU5ULMXMPujCK8JwBA6olGY02rJ9sekeIh0IFx0sUXOPSJQWiyrekfguyiUTYGFCYIGJHTU5467iyughjft7dygvjgftdr7utyiugvjgcydrytucyfg78tiyuhgfibdjlshiuocgmijrfngviywo8ytcmoilakjòhwgpisoòljdsmogyub')
ENV = os.getenv('ENV', 'development').lower()
_DEFAULT_JWT_SECRET = 'f4buctOtskxFmHeYIU5ULMXMPujCK8JwBA6olGY02rJ9sekeIh0IFx0sUXOPSJQWiyrekfguyiUTYGFCYIGJHTU5467iyughjft7dygvjgftdr7utyiugvjgcydrytucyfg78tiyuhgfibdjlshiuocgmijrfngviywo8ytcmoilakjòhwgpisoòljdsmogyub'
JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    if ENV == 'development':
        JWT_SECRET = _DEFAULT_JWT_SECRET
        # Optionally, print a warning
        print("Warning: Using default JWT secret in development environment.")
    else:
        raise RuntimeError("JWT_SECRET environment variable must be set in production environment.")
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))

# Weather
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_BASE_URL = os.getenv('WEATHER_BASE_URL')

# Agents
CONVERSATION_AGENT_URL = os.getenv('CONVERSATION_AGENT_URL')
WEATHER_AGENT_URL = os.getenv('WEATHER_AGENT_URL')
ACTIVITY_AGENT_URL = os.getenv('ACTIVITY_AGENT_URL')
PACKING_AGENT_URL = os.getenv('PACKING_AGENT_URL')
ORCHESTRATOR_AGENT_URL = os.getenv('ORCHESTRATOR_AGENT_URL')

# OAuth2 - Google
OAUTH_GOOGLE_CLIENT_ID = os.getenv('OAUTH_GOOGLE_CLIENT_ID')
OAUTH_GOOGLE_CLIENT_SECRET = os.getenv('OAUTH_GOOGLE_CLIENT_SECRET')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

GOOGLE_AUTHORIZATION_URI = os.getenv('GOOGLE_AUTHORIZATION_URI')
GOOGLE_TOKEN_URI = os.getenv('GOOGLE_TOKEN_URI')
GOOGLE_USERINFO_URI = os.getenv('GOOGLE_USERINFO_URI')

# Email
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')

# Activity Recommender
ACTIVITY_FAISS_DIR = os.getenv('ACTIVITY_FAISS_DIR', "data/activity_faiss")
ACTIVITY_SOURCES_JSON = os.getenv('ACTIVITY_SOURCES_JSON', "data/activity_sources.json")

ORCHESTRATOR_CHROMA_DIR = os.getenv('ORCHESTRATOR_CHROMA_DIR', "data/orchestrator_chroma")

# Geocoder (OpenStreetMap Nominatim) - optional
# Set GEOCODER_ENABLE=true in .env to enable remote geocoding lookups
GEOCODER_ENABLE = os.getenv('GEOCODER_ENABLE', 'false').lower() in ('1', 'true', 'yes')
GEOCODER_USER_AGENT = os.getenv('GEOCODER_USER_AGENT', 'seasonal-travel-recommender/1.0 (contact: you@example.com)')
GEOCODER_CACHE_PATH = os.getenv('GEOCODER_CACHE_PATH', os.path.join(BASE_DIR, 'data', 'geocode_cache.json'))