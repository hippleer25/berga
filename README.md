# Berga

Berga is a self-hosted, smart RSS reader that gives you full control over your content and your data. Built aiming privacy and power, Berga uses an open-source recommendation algorithm to rank, aggregate, and organize your feeds - while remaining fully customizable and even optional.

Berga learns your preferences automatically through NLP-powered vector affinity, surfacing the most relevant content to you. At the same time, you can fine-tune or override every aspect of the algorithm: boost topics you care about, suppress ones you don't, or disable personalization entirely.

Deploy with Docker and access Berga from any browser, install it as a PWA on mobile, or use the native Android app.

## Features

### Smart Recommendations
- NLP-powered recommendation engine based on vector affinity between content and your preferences
- Like, dislike, and save articles to train your personalized feed
- Fully tunable algorithm — manually boost or suppress any topic
- Cold-start and chronological fallback modes for new users
- Publisher diversity controls to avoid echo chambers

### AI-Powered Tools
- **Mota** — AI chatbot that searches your feeds and the web (local, online, or mixed modes)
- Article summarization with a single click (SSE streaming)
- Weekly event clustering with AI-generated headlines
- Similar article discovery via vector search

### Feed Management
- Smart RSS/Atom feed discovery — crawl any URL to find feeds automatically
- Search the web for new feeds by topic (DuckDuckGo integration)
- Organize feeds into nested folders
- Import and export OPML files
- Multi-user support with fully isolated data

### Reader Experience
- Built-in article reader with text extraction and HTML rendering
- Infinite scroll and responsive design for desktop and mobile
- Customizable themes and fonts (Inter, Figtree, Karla, Manrope, Newsreader, Playfair Display, Vollkorn)
- Available as a PWA or native Android app (Capacitor)

### Privacy & Control
- Fully self-hosted — your database never leaves your server
- Open-source recommendation algorithm you can inspect and modify
- SSRF protection for feed URLs
- JWT-based authentication with secure httponly cookies

### Internationalization
- Available in English, French, Spanish, German, and Portuguese
- Localized LLM prompts and search results per language

## Quick Start
### 1. Clone the Repository
```bash
git clone https://github.com/your-org/berga.git
cd berga
```

### 2. Configure environment variables
```
cp .env.example .env
nano .env
```

### 3. Start docker
```
docker compose up -d 
```

Everything is done! You can start using Berga!!