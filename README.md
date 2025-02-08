# Superteam Vietnam Community Platform

An AI-enhanced community management platform for Superteam Vietnam featuring local LLM deployment, multi-channel communication, and comprehensive admin tools.

## 🌟 Features

- 🤖 Local LLM-powered chatbot with RAG system
- 📱 Multi-channel support (Telegram + Twitter)
- 👥 Smart member management and skill matching
- 📚 Document management with AI processing
- 🔒 Privacy-first architecture
- 🎯 Intuitive admin interface

## 🛠️ Technology Stack

- **Backend:** FastAPI, Python
- **Database:** SQLite, SQLAlchemy
- **AI/ML:** LangChain, LlamaCpp
- **Vector Store:** ChromaDB
- **Frontend:** Tailwind CSS
- **Bot Frameworks:** python-telegram-bot, tweepy

## 📋 Prerequisites

- Python 3.9+
- Local LLM model (llama-2-7b-chat.Q4_K_M.gguf)
- SQLite
- Node.js (for frontend development)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/vijaygopalbalasa/superteam-vietnam.git
   cd superteam-vietnam
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the application**
   ```bash
   python -m app.main
   ```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# Base Configuration
SECRET_KEY=your_secret_key
ADMIN_PASSWORD=your_admin_password

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_IDS=comma,separated,admin,ids

# Twitter Configuration (Optional)
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_SECRET=your_twitter_access_secret
```

## 📁 Project Structure

```
superteam-vietnam/
├── app/
│   ├── bots/               # Bot implementations
│   ├── core/               # Core functionality
│   ├── ui/                 # Admin interface
│   └── main.py            # Application entry point
├── data/
│   ├── knowledge_base/    # RAG system documents
│   ├── models/            # Local LLM models
│   └── uploads/           # User uploads
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## 🤖 Bot Commands

- `/start` - Initialize the bot
- `/help` - Show help message
- `/find <skills>` - Find members by skills
- `/upload` - Upload documents (admin only)
- `/tweet` - Create tweet draft (admin only)
- `/improve` - Get AI suggestions for tweet (admin only)
- `/publish` - Post tweet (admin only)

## 🔐 Privacy & Security

- Local LLM deployment ensures data sovereignty
- No external API dependencies for AI processing
- Secure admin interface with authentication
- Role-based access control
- Encrypted data storage

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
