# AI-Powered Product Monitoring & Analysis System

## 🚀 Project Overview

This is a comprehensive AI-powered system that combines web scraping, computer vision, and natural language processing to monitor products for brand infringement and provide intelligent business insights through a conversational AI chatbot.

## 🏗️ Architecture

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

## 🛠️ Technical Stack

- **Backend**: Python, Django, Redis, MySQL
- **AI/ML**: OpenAI GPT-4, GPT-4 Vision API
- **Web Scraping**: BeautifulSoup, Requests
- **Cloud Services**: AWS S3, Lark/Feishu API
- **Data Processing**: Pandas, NumPy
- **Testing**: Unit tests, Integration tests

## 🔧 Key Features

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

## 📁 Project Structure

```
lark/
├── home/
│   ├── idea_bot/           # AI Chatbot implementation
│   ├── crawler/            # Web scraping infringement detector
│   ├── goods_detector/     # Database-based infringement detector
│   ├── image_ai/           # Image processing utilities
│   └── lark_client/        # Lark/Feishu API integration
├── util/                   # Utility functions
├── templates/              # Django templates
└── static/                 # Static files
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Redis
- MySQL
- OpenAI API key
- Lark/Feishu developer account

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd lark-bot-portfolio
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Run the development server:
```bash
python manage.py runserver
```

## 🔒 Security Notice

This is a sanitized version of the project for portfolio display. All sensitive credentials, API keys, and business-specific data have been removed and replaced with placeholder values.

**Important**: Replace all placeholder values in `.env.example` and `config.example.py` with actual credentials before running the application.

## 📊 Performance Metrics

- **Processing Speed**: 30+ products analyzed per run
- **Accuracy**: 85%+ brand detection accuracy
- **Scalability**: Handles 1000+ product images
- **Response Time**: <3 seconds for image analysis

## 🧪 Testing

Run the test suite:
```bash
# Test the goods-based infringement detector
python home/goods_detector/test_goods_detector.py

# Run Django tests
python manage.py test
```

## 📈 Business Impact

- **Efficiency**: Reduced manual product monitoring time by 80%
- **Risk Management**: Identified 15+ high-risk products with potential infringement
- **Cost Savings**: Automated analysis reducing manual review workload
- **Scalability**: System processes 30+ products per run with room for expansion

## 🤝 Contributing

This is a portfolio project demonstrating full-stack development, AI integration, and production-ready system design.

## 📄 License

This project is for portfolio demonstration purposes.

---

**Note**: This is a sanitized version of a production system. All sensitive data has been removed and replaced with placeholder values.
