# 🚀 LookFor Hackathon 2026 - Context Prompt (Post-Merge)

## Proje Özeti
LookFor Hackathon 2026 için multi-agent customer support sistemi MVP'si. 3 use-case: WISMO (Where Is My Order), Wrong/Missing Item, Refund Request.

## Teknoloji Stack
- **Backend**: Python + FastAPI
- **LLM**: OpenAI GPT-4o mini
- **Storage**: In-memory (dict-based)
- **Workflow**: JSON-based deterministic decision trees

---

## ✅ Tamamlanan Modüller (Dev A)

### 1. Session Management
- `app/store.py` → InMemory SessionStore
- `app/models.py` → Session, Message, TraceEvent, CaseContext, Intent enum
- **Endpoints**: `/session/start`, `/session/{id}/message`, `/session/{id}/trace`

### 2. Orchestrator (`app/orchestrator.py`)
- Agent pipeline: Triage → Workflow → Action/Support/Escalation
- Escalated session lock
- Agent injection: `set_triage_agent()`, `set_action_agent()`, etc.

### 3. Workflow Engine (`app/workflow/__init__.py`)
- JSON-based deterministic rules (NO LLM policy decisions!)
- Workflows: `workflows/wismo.json`, `workflows/wrong_missing.json`, `workflows/refund_standard.json`
- Returns: `next_action` (respond | call_tool | ask_clarifying | escalate | route_to_workflow)

### 4. ToolsClient (`app/tools/client.py`)
- Centralized tool execution
- JSON Schema param validation
- 1 retry on failure
- 19 official Shopify/Skio tools in `tools/catalog.json`
- Mock mode enabled by default

### 5. Support Agent (`app/agents/support.py`)
- LLM response generation
- Template fallback
- Brand tone: empatik, profesyonel, Türkçe

### 6. Escalation Agent (`app/agents/escalation.py`)
- Structured JSON payload (hackathon schema compliant)
- Session lock
- Priority calculation

### 7. TicketStore (`app/tickets.py`)
- Interface ready for real ticket dataset
- Dummy fixtures: `fixtures/tickets_dummy.json`

### 8. Observability (`app/trace.py`)
- TraceLogger for all events
- Event types: customer_message, triage_result, workflow_decision, tool_call, agent_response, escalation

---

## 📊 Test Coverage
- **58 tests passing**
- Test files: `test_session.py`, `test_smoke.py`, `test_workflow.py`, `test_tools.py`, `test_escalation.py`, `test_integration.py`, `test_tickets.py`

---

## ⏳ Dev B Tarafından Eklenmesi Beklenen

### Triage Agent
- Mesaj classification (WISMO/Wrong-Missing/Refund)
- Entity extraction (order_id, tracking_number, item_name)
- OpenAI GPT-4o mini + structured output

### Action Agent
- Workflow'un `call_tool` kararı verdiğinde tool execution
- Session context'ten param resolution
- Detaylar: `docs/ACTION_AGENT_TASK.md`

---

## 🔌 Entegrasyon Noktaları

Dev B'nin agent'ları şu şekilde bağlanır:

```python
# app/orchestrator.py → wire_agents() fonksiyonunda
from app.agents.triage import triage_agent
from app.agents.action import action_agent

orchestrator.set_triage_agent(triage_agent)
orchestrator.set_action_agent(action_agent)
```

---

## 📁 Dosya Yapısı

```
app/
├── api.py              # FastAPI endpoints
├── orchestrator.py     # Agent pipeline coordinator
├── store.py            # Session store
├── models.py           # Pydantic models
├── tickets.py          # TicketStore
├── trace.py            # Observability
├── workflow/
│   └── __init__.py     # WorkflowEngine
├── tools/
│   └── client.py       # ToolsClient
└── agents/
    ├── support.py      # SupportAgent ✅
    ├── escalation.py   # EscalationAgent ✅
    ├── triage.py       # TriageAgent (Dev B)
    └── action.py       # ActionAgent (Dev B)

workflows/
├── wismo.json
├── wrong_missing.json
└── refund_standard.json

tools/
└── catalog.json        # 19 official tools + JSON schemas

tests/                  # 58 tests
```

---

## 🎯 Sonraki Adımlar

1. [ ] Dev B merge sonrası Triage + Action Agent entegrasyonu test et
2. [ ] Full end-to-end demo senaryoları çalıştır
3. [ ] Ticket dataset gelince `ticket_store.ingest_from_file()` çağır
4. [ ] Demo hazırlığı

---

## Çalıştırma

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

---

## Önemli Notlar

1. **Policy kararları ASLA LLM'e bırakılmaz** - WorkflowEngine deterministik
2. **Escalation schema** hackathon gereksinimlerine uyumlu
3. **ToolsClient mock_mode=True** - gerçek API için False yapılmalı
4. **Session lock** - escalated session yeni mesaj kabul etmez
