# Test Setup

## Prerequisites

### 1. Server Must Be Running

Before running tests, start the FastAPI server:

```bash
# Windows
.\.venv\Scripts\python.exe main.py

# Linux/Mac
python main.py
```

The server should be running at `http://localhost:8000`.

### 2. Environment Variables (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` | API base URL |

To use a different URL:
```bash
set BASE_URL=http://localhost:3000
pytest tests/test_api_contract.py -v
```

### 3. Mock Mode

Mock mode is **enabled by default** in `ToolsClient`. This ensures:
- Deterministic responses for testing
- No external API dependencies
- Predictable tool failure scenarios (e.g., `#INVALID_FOR_TEST`)

## Running Tests

```bash
# Run all contract tests (verbose)
.\.venv\Scripts\python.exe -m pytest tests/test_api_contract.py -v

# Run all contract tests (quiet)
.\.venv\Scripts\python.exe -m pytest tests/test_api_contract.py -q

# Run specific test
.\.venv\Scripts\python.exe -m pytest tests/test_api_contract.py::TestAPIContract::test_session_start_contract -v

# Run all tests
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

## Deterministic Test Scenarios

| Scenario | Trigger | Expected Behavior |
|----------|---------|-------------------|
| Tool failure | Order ID contains `INVALID_FOR_TEST` | Returns `success: false` with "Order not found" error |
| Escalation | Tool failure or policy boundary | Session locks, escalation payload created |
| Session lock | Post-escalation messages | No new tool calls, locked message returned |

## Troubleshooting

1. **Connection refused**: Ensure server is running at the correct URL
2. **Test timeout**: Increase `TIMEOUT` in test file (default: 30s)
3. **Mock failures not triggering**: Verify `#INVALID_FOR_TEST` is in the order ID
