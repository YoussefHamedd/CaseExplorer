# Case Explorer

A web interface and API for exploring Maryland court case data scraped from [Maryland Judiciary Case Search](http://casesearch.courts.state.md.us/casesearch/inquiry-index.jsp) by [Case Harvester](https://github.com/YoussefHamedd/CaseHarvester).

Built with React (frontend) and Flask (backend API), deployed via Docker.

---

## Features

- **All Cases** — Browse all cases including unscraped skeleton entries (not just fully parsed ones)
- **Foreclosure Explorer** — Filter & search FC/ROR cases by date, county, status, judge
- **Redemption Explorer** — Dedicated view for Right of Redemption cases
- **Admin Dashboard** — Live stats: scraper queue, parser queue, FC enumeration spider progress, DB counts
- **REST API** — Paginated endpoints for cases, foreclosures, stats

---

## Architecture

```
Browser → Nginx → React Frontend
                → Flask API → PostgreSQL (mjcs DB)
                            → Redis (queue stats)
                            → MinIO (case HTML files)
```

---

## Setup

### Prerequisites
- Docker + Docker Compose
- PostgreSQL database (mjcs)
- Redis
- MinIO (S3-compatible object storage)

### Environment Variables

Create a `.env` file at the root:

```env
SQLALCHEMY_DATABASE_URI_PRODUCTION=postgresql://user:pass@host:5432/mjcs
SQLALCHEMY_DATABASE_URI_DEVELOPMENT=postgresql://user:pass@host:5432/mjcs
REDIS_URL=redis://localhost:6379
```

### Run with Docker

```bash
docker compose up -d
```

Frontend available at `http://localhost:3000`  
API available at `http://localhost:5000`

---

## FC Enumeration Spider

The `fc_enum_spider.py` script (in CaseHarvester) discovers Foreclosure and Right of Redemption cases by enumerating every possible case number sequence:

```
C-{county}-CV-{year}-{sequence:06d}
```

- Runs as 2 instances (split by county)
- 10 workers per instance
- Inserts found cases directly to DB + pushes to scraper queue
- Progress tracked in `fc_enum_progress.json` (read by Admin UI)
- Blocked sequences are retried forever (never dropped)

---

## Development

```bash
# Install dependencies
npm install
cd server && pip install -r requirements.txt

# Run dev server
make start_dev
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cases/count` | Total case count |
| POST | `/api/v1/foreclosure/active` | FC/ROR cases (paginated, filterable) |
| GET | `/api/v1/admin/status` | Live system stats |
| POST | `/api/v1/cases` | All cases (paginated) |

