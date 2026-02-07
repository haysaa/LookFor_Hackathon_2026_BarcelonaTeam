# LookFor_Hackathon_2026_BarcelonaTeam

Multi-agent customer support system for WISMO, Refund, and Wrong/Missing Item use cases.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

Server runs at `http://localhost:8000`

## Loading Real Tickets

By default, the app loads dummy tickets from `fixtures/tickets_dummy.json`.

To load real anonymized tickets:

```bash
# Option 1: Set environment variable
set TICKETS_PATH=fixtures/tickets_real.json
python main.py

# Option 2: Use runtime path
set TICKETS_PATH=/mnt/data/anonymized_tickets.json
python main.py
```

The loader auto-detects format (real vs dummy) and logs the source at startup.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/start` | POST | Start new session |
| `/session/{id}/message` | POST | Send message |
| `/session/{id}/trace` | GET | Get session trace |
| `/health` | GET | Health check |

## Tests

```bash
# All tests
pytest tests/ -v

# API contract tests
pytest tests/test_api_contract.py -v

# Ticket store tests
pytest tests/test_ticket_store_real_tickets.py -v

# WISMO workflow tests
pytest tests/test_wismo_workflow.py -v
```

## WISMO Promise Logic

The WISMO (Where Is My Order) workflow includes day-based delivery promise rules:

| Customer Contacts | Promise | Deadline |
|-------------------|---------|----------|
| Mon–Wed | "by Friday" | Friday of current week |
| Thu–Sun | "early next week" | Next Monday |

**Session Context Fields Stored:**
- `wismo_promise_type`: `FRIDAY` or `EARLY_NEXT_WEEK`
- `wismo_promise_deadline`: ISO date (YYYY-MM-DD)
- `wismo_promise_set_at`: ISO timestamp

**Post-Promise Flow:**
- If customer contacts again after deadline and order not delivered → **escalate**
- Escalation reason: "WISMO promised date passed; requires human to process resend"
- Session locked (no more automatic replies)
