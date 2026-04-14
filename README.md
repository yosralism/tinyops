# tinyops

An on-prem, Python Network Management System for large ISPs. Tinyops focuses on reliable data collection from thousands of routers via SSH, Telnet, and SNMP, parsing outputs into structured data, and providing extensible workflows for inventory, notifications, and future AI-driven insights.

## Key Goals
- Reliable multi-protocol collectors with bastion/jump support.
- Scheduled and ad-hoc job orchestration with isolated execution.
- Parser pipeline producing structured facts and raw artifacts.
- Secure user sessions, RBAC, and integrations (Telegram, email, Webex, SNMP traps).
- Observability, CI/CD, documentation, and future topology/RAG capabilities.

## Getting Started
1. Clone the repo.
2. Create and activate a virtual environment.
3. Install dependencies (see Development Setup).
4. Review [`docs/ARCHITECTURE_AND_ROADMAP.md`](docs/ARCHITECTURE_AND_ROADMAP.md) for architecture, stack, and development roadmap.
5. Check `/infra` for deployment assets.

## Development Setup

1. **Create and activate a virtual environment**
   python3 -m venv .venv
   source .venv/bin/activate

2. **Install dependencies**
   - Using requirements files:
     pip install -r requirements/dev.txt
   - If using Poetry:
     poetry install --with dev

3. **Run tests and linting (placeholders for now)**
   pytest
   ruff check .

## Running the API locally

With your virtual environment active:

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

or

```bash
./scripts/run_api.sh
```

### Environment Variables

Copy `.env_sample` to `.env` and adjust for your environment:

```bash
cp .env_sample .env