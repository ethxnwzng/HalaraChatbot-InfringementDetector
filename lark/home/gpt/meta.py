"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use the API key directly for now
API_KEY = "your_api_key_here"
OPEN_AI_KEY_DFS = API_KEY
OPEN_AI_KEY_AIGC = API_KEY

# Standard OpenAI model names
MODEL_CHAT_3_5 = 'gpt-3.5-turbo'
MODEL_CHAT_4 = 'gpt-4'
MODEL_CHAT_4_TURBO = 'gpt-4-1106-preview'  # Updated to latest GPT-4 Turbo
MODEL_CHAT_4_O = 'gpt-4'  # Changed to standard GPT-4

# Default models for different purposes
MODEL_CHAT = MODEL_CHAT_4  # Changed to standard GPT-4
MODEL_REVIEW = MODEL_CHAT_4_TURBO

# Lark chat configurations
LARK_CHAT_GPT_4_ADS = 'oc_eaf81600be37424fdf033ba9a7e33a4c'
LARK_CHAT_GPT_4_VIP = 'oc_aee6fb383282ad5b554e237c6439d93b'

CHAT_BOT_NAME = 'lark_bot'
TIMEOUT_CHAT_CONTEXT = 60 * 60  # 1 hour in seconds

