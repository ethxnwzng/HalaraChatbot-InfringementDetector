# Halara Chatbot and a product Infringement Detector

## Project Overview

This is a comprehensive AI-powered system that combines web scraping, computer vision, and natural language processing to monitor products for brand infringement and provide intelligent business insights through a conversational AI chatbot.

## Architecture

### Core Components

1. **AI-Powered Business Intelligence Chatbot** (`home/idea_bot/`)
   - Django-based chatbot with OpenAI GPT-4 Vision integration
   - File analysis (CSV, Excel, PDF, Images) with context-aware responses
   - Redis session management and conversation persistence
   - Lark/Feishu platform integration with OAuth2 authentication

2. **Automated Brand Infringement Detection System**
   - **Web Crawler Version** (`home/crawler/`): BeautifulSoup-based scraper with intelligent pagination
   - **Database Version** (`home/goods_detector/`): Direct database integration for faster processing
   - GPT-4 Vision API integration for brand logo and design element detection
   - Automated reporting with Lark spreadsheet integration

## Tech Stack

- **Backend**: Python, Django, Redis, MySQL
- **AI/ML**: OpenAI GPT-4, GPT-4 Vision API
- **Web Scraping**: BeautifulSoup, Requests
- **Cloud Services**: AWS S3, Lark/Feishu API
- **Data Processing**: Pandas, NumPy
- **Testing**: Unit tests, Integration tests

## Key Features

### Chatbot Capabilities
- Multi-format file analysis (CSV, Excel, PDF, Images)
- Context-aware conversations with memory retention
- Real-time image analysis using GPT-4 Vision
- Business data insights and reporting
- Multilingual support (Chinese/English)

### Infringement Detection
- Automated product discovery and crawling
- AI-powered brand logo and design element detection
- Risk assessment and scoring
- Automated report generation with embedded images
- Duplicate detection and incremental processing

## Security Notice

This is a sanitized version of the project for portfolio display. All sensitive credentials, API keys, and business-specific data have been removed and replaced with placeholder values.

**Important**: Replace all placeholder values in `.env.example` and `config.example.py` with actual credentials before running the application.

## Performance Metrics
### idea_bot Chatbot:

### Infringement Detector:
- **Processing Speed**: 30+ products analyzed per run
- **Accuracy**: 85%+ brand detection accuracy
- **Scalability**: Handles 1000+ product images
- **Response Time**: <3 seconds for image analysis

## Business Impact
   
### idea_bot Chatbot:

### Infringement Detector
- **Efficiency**: Reduced manual product monitoring time by 80%
- **Risk Management**: Identified 15+ high-risk products with potential infringement
- **Cost Savings**: Automated analysis reducing manual review workload
- **Scalability**: System processes 30+ products per run with room for expansion
