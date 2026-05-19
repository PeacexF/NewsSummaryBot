# RSS News Summarizer Telegram Bot

A Telegram bot that collects news from RSS feeds, processes them, and delivers AI-generated summaries directly to users.

The project is designed as a modular pipeline:  
`data collection → filtering → processing → delivery`

---

## Main Idea

The system follows a pipeline approach:

1. Collect RSS feed data from a self hosted rsshub
2. Normalize and prepare raw articles  
3. Filter and remove irrelevant or duplicate content  
4. Process articles into short summaries using an LLM  
5. Deliver results through a Telegram bot interface  

---

## Project Structure

``` text
├── Dockerfile
├── RSSHUB
│   └── docker-compose.yml
├── bot
│   ├── handlers.py
│   └── main.py
├── client
│   ├── parser.py
│   ├── rss.py
│   └── run_collector.py
├── database
│   ├── database.py
│   └── models.py
├── docker-compose.yml
├── log
│   ├── log.log
│   └── log.py
├── process
│   ├── filter.py
│   └── gemini.py
````

---

## Components

### Bot Layer
Handles Telegram interaction:
- receives user requests
- sends processed news summaries

---

### Client Layer
Responsible for collecting and preparing RSS data:
- fetching RSS feeds
- parsing raw feed data

---

### Processing Layer
Responsible for transforming raw articles into usable content:
- filtering irrelevant or duplicate items
- generating summaries using an LLM

---

### Database Layer
Handles storage:
- stores articles and processed results
- maintains state

---

### Logging
Centralized logging system for debugging and monitoring

---

## Deployment

The project is designed to run using Docker:

```bash
docker-compose up --build
````

Optional RSSHub integration is included for self hosted RSSHubs, you may need it as Clouflare blocks requests on a public RSSHub

---

## Requirements

* Python 3.10+
* Docker & Docker Compose
* Telegram Bot Token
* LLM API key for summarization
* (Optional) A Server for RSSHub

---

## Environment Variables

```
RSSHUB_BASE="http://ip:port_of_your_server/telegram/channel/{channel}"
TELEGRAM_BOT_TOKEN=your_token
GEMINI_API_KEY=your_key
DATABASE_URL=your_database_url
```

---

## Goals of the Project

* Automate news collection from RSS feeds
* Reduce information overload via summarization
* Deliver content in a simple Telegram interface
* Maintain a modular and extendable architecture

---

## License

This project is open-source under the MIT License.  
**If you use this project commercially, consider contributing improvements back upstream.**

---

## Disclaimer

All content is sourced from public RSS feeds. The project does not claim ownership of external articles; all rights belong to original publishers.

---

## Contributing

Contributions are welcome as always.