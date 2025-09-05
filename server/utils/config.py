import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="C:/Users/dulha/GitHub/Seasonal_Travel_Recommender/server/.env")

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# CORS
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS')

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')

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
ACTIVITY_FAISS_DIR = os.getenv('ACTIVITY_FAISS_DIR', "../../data/activity_faiss")
ACTIVITY_SOURCES_JSON = os.getenv('ACTIVITY_SOURCES_JSON', "../../data/activity_sources.json")
