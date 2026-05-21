# News Summarizer Telegram Bot

A Telegram bot that collects news from RSS feeds, processes them, deduplicates them, and delivers AI-generated summaries.

The project is designed as a modular pipeline:  
`data collection → storage → filtering → processing → delivery`

---

## Main Idea

The system follows a pipeline approach:

1. Collect RSS feed data from a self hosted rsshub
2. Normalize and prepare raw articles
3. Store them into the Database
4. Filter and remove irrelevant or duplicate content  
5. Process articles into short summaries using an LLM  
6. Deliver results through a Telegram bot interface  

---

## Project Structure

``` text
├── Dockerfile
├── docker-compose.yml
├── main.py
├── bot
│   ├── handlers.py
│   └── main.py
├── client
│   ├── parser.py
│   └── rss.py
├── database
│   ├── database.py
│   ├── models.py
│   └── repository.py
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
- gives access to the results for the processing layer

---

### Logging
Centralized logging system for debugging and monitoring

---

## Deployment

The project is designed to run using Docker:

```bash
docker-compose up --build
````

Optional RSSHub integration is included for self hosted RSSHubs, you may need it as Clouflare **blocks** requests on a public RSSHub

---

## Requirements

* Python 3.10+
* Docker & Docker Compose
* Telegram Bot Token
* LLM API key for summarization
* (Optional) A Server for RSSHub and Postgresql

---

## Environment Variables

```
TELEGRAM_BOT_TOKEN=token

GEMINI_API_KEY=key

RSSHUB_BASE="http://ip:1200/telegram/channel/{channel}"

DB_USER=user

DB_PASSWORD=password

DB_NAME=name

DATABASE_URL=postgresql+asyncpg://user:password@ip:5432/name
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