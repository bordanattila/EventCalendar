# Calendar Agent Service

An AI-powered calendar agent that understands natural language commands and manages your calendar events.

## Features

- **Natural Language Interface**: Send commands like "Add soccer every Tuesday at 6pm for 8 weeks"
- **Human-in-the-Loop**: Agent proposes changes, you approve before committing
- **Conflict Detection**: Automatically detects scheduling conflicts
- **Recurring Events**: Full support for daily, weekly, monthly, and yearly recurrence
- **Structured Plans**: Returns machine-readable action plans

## Quick Start

### 1. Install Dependencies

```bash
cd agent_service
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run the Server

```bash
uvicorn calendar_agent.main:app --reload
```

Or:

```bash
python -m calendar_agent.main
```

## API Endpoints

### Health Check
```
GET /health
```

### Chat (Propose Actions)
```
POST /chat
Content-Type: application/json

{
    "message": "Add soccer every Tuesday at 6pm for 8 weeks"
}
```

Response:
```json
{
    "summary": "Added soccer Tuesdays 6pm for 8 weeks starting 2025-01-07.",
    "actions": [
        {
            "type": "create_event",
            "title": "Soccer",
            "start": "2025-01-07T18:00:00-05:00",
            "end": "2025-01-07T19:00:00-05:00",
            "recurrence": {"freq": "weekly", "byweekday": ["TU"], "count": 8}
        }
    ],
    "warnings": [],
    "needs_approval": true,
    "plan_id": "plan_abc123"
}
```

### Commit (Apply Approved Plan)
```
POST /commit
Content-Type: application/json

{
    "plan_id": "plan_abc123"
}
```

### Events CRUD (Debug)
```
GET /events                    # List all events
GET /events/{id}              # Get single event
POST /events                  # Create event
PUT /events/{id}              # Update event
DELETE /events/{id}           # Delete event
```

## Example Commands

```
"Add soccer every Tuesday at 6pm for 8 weeks"
"Move dentist if it conflicts with work"
"What are my crunch days next week?"
"Schedule team standup daily at 9am starting Monday"
"Cancel all meetings tomorrow"
"Show me my free time on Friday afternoon"
"Add birthday party on March 15th from 2pm to 6pm at John's house"
```

## Architecture

```
agent_service/
├── src/calendar_agent/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── api/                 # Route handlers
│   ├── agent/               # LangChain agent logic
│   ├── tools/               # Agent tools
│   ├── db/                  # Database layer
│   └── util/                # Helpers
└── tests/                   # Test suite
```

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black src/ tests/
ruff check src/ tests/ --fix
```

## License

MIT

