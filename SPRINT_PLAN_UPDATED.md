# Lookfor Hackathon 2026 - Sprint Plan (2 Gün)

**Takım**: 2 Developer (Dev A + Dev B)  
**Platform**: OpenAI API (GPT-4o mini) + deterministic workflow engine  
**Hedef**: WISMO, Refund, Wrong/Missing Item için çalışan multi-agent email support sistemi

---

## 🎯 Sprint Hedefleri

- [x] 3 use-case için end-to-end akış çalışır durumda
- [x] Session yönetimi + escalation logic
- [x] Tool entegrasyonu (Shopify/Skio official handles)
- [x] Observable trace system (decisions, tools, actions)
- [x] Demo senaryolarının tümü geçer
- [x] Canlı demo yapılabilir durumda sunum

---

## 📧 Email Session Start Requirements

**Session start MUST accept:**
```json
{
  "customer_email": "customer@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "shopify_customer_id": "cust_XXXXXXXX"
}
```

**Multi-Turn Session Handling:**
- Continuous memory across messages
- No contradictions between turns
- Behaves like real email thread
- Session context preserved until resolved/escalated

---

## 🎫 Ticket Dataset Plan (Arrival Tomorrow)

### Today: Build Infrastructure Without Tickets
- [ ] Create `TicketStore` interface (abstract layer)
- [ ] Create `DummyTicketStore` with 3-5 fixture tickets per use-case
- [ ] Build ticket parsing logic for expected format

### Tomorrow: Ingest Real Dataset
- [ ] Parse real ticket JSON (no architecture refactor needed)
- [ ] Populate `TicketStore` with real data
- [ ] (Optional) RAG-lite similarity search for Support Agent prompts

**Expected Ticket Format:**
```json
{
  "conversationId": "<UUID@email.com>",
  "customerId": "cust_XXXXXXXX",
  "createdAt": "DD-MMM-YYYY HH:mm:ss",
  "ConversationType": "email",
  "subject": "string",
  "conversation": "string"
}
```

---

## 🔧 Official Tool Handles (Hackathon Spec)

### Shopify Tools
| Handle | Purpose |
|--------|---------|
| `shopify_add_tags` | Add tags to order/customer |
| `shopify_cancel_order` | Cancel an order |
| `shopify_create_discount_code` | Create discount code |
| `shopify_create_draft_order` | Create draft order |
| `shopify_create_return` | Create return request |
| `shopify_create_store_credit` | Issue store credit |
| `shopify_get_collection_recommendations` | Get collection recommendations |
| `shopify_get_customer_orders` | Get customer's orders |
| `shopify_get_order_details` | Get order details |
| `shopify_get_product_details` | Get product details |
| `shopify_get_product_recommendations` | Get product recommendations |
| `shopify_get_related_knowledge_source` | Get FAQ/knowledge |
| `shopify_refund_order` | Process refund |
| `shopify_update_order_shipping_address` | Update shipping address |

### Skio Tools (Subscriptions)
| Handle | Purpose |
|--------|---------|
| `skio_cancel_subscription` | Cancel subscription |
| `skio_get_subscription_status` | Get subscription status |
| `skio_pause_subscription` | Pause subscription |
| `skio_skip_next_order_subscription` | Skip next order |
| `skio_unpause_subscription` | Unpause subscription |

---

## 🌐 Uniform API Response Contract

All tool endpoints return HTTP 200 with this structure:

**Success:**
```json
{"success": true}
// or
{"success": true, "data": {...}}
```

**Failure:**
```json
{"success": false, "error": "Error description"}
```

**ToolsClient Requirements:**
- [ ] Enforce HTTP 200 contract parsing
- [ ] Normalize all responses to `{success, data?, error?}`
- [ ] JSON-schema validation on params BEFORE calling tools
- [ ] Log every tool call (input/output) to trace
- [ ] Implement 1 retry on transient failures

---

## 📅 Gün 1 - Temel Altyapı + İlk Akış

### Sabah (09:00 - 13:00) - **4 saat**

#### Dev A - Session & Orchestrator Core
**Süre**: 3.5 saat

- [ ] **Session State modeli** (30dk)
  - `Session` dataclass with email session fields:
    - `customer_email`, `first_name`, `last_name`, `shopify_customer_id`
    - `messages[]`, `intent`, `case_context`, `tool_history[]`, `status`
  - In-memory store (dict based)
  - Multi-turn message history with continuous memory
  
- [ ] **Session endpoints** (1 saat)
  - `POST /session/start` - Accept email session fields (email, first/last name, shopify_customer_id)
  - `POST /session/{id}/message` - Receive email, orchestrator handles
  - `GET /session/{id}/trace` - Return observable timeline JSON

- [ ] **Orchestrator logic** (2 saat)
  - Session status kontrolü (escalated ise durma = session lock)
  - Agent call sequence: triage → workflow → (action?) → support
  - Escalation triggers → lock session
  - Record every step to trace

**Çıktı**: `/session/start` ve `/message` çalışıyor

**⚠️ Test Gate**: 
- [ ] Smoke test: /start + /message endpoints 200 döner
- [ ] Session start accepts all required fields (email, first_name, last_name, shopify_customer_id)
- [ ] Multi-turn: 2nd message retrieves context from 1st

---

#### Dev B - Agent Prompts & Triage Agent
**Süre**: 3.5 saat

- [ ] **Prompt template sistemi** (45dk)
  - `prompts/` folder with `.txt` templates
  - Jinja2 variable rendering
  - Version numbers (v1.0)
  
- [ ] **Triage Agent implementasyonu** (2.5 saat)
  - OpenAI API (GPT-4o mini) + structured JSON outputs
  - Intent classification: WISMO / REFUND_STANDARD / WRONG_MISSING
  - Entity extraction: order_id, tracking_number, item_name
  - Output: `TriageResult` schema
  - Auto-flag `needs_human=true` if confidence < 0.6

**Çıktı**: Triage Agent mesajları doğru sınıflandırıyor

**⚠️ Test Gate**: 
- [ ] 6 sample messages intent test
- [ ] Entity extraction test (order_id, etc.)

---

### Öğle Arası (13:00 - 14:00)

---

### Öğleden Sonra (14:00 - 18:00) - **4 saat**

#### Dev A - Workflow Engine (Deterministik Policy)
**Süre**: 4 saat

- [ ] **WorkflowEngine (JSON loader + evaluator)** (2.5 saat)
  - Read decision trees from `workflows/*.json`
  - Input: intent + case_context + tool_result
  - Output: `WorkflowDecision` JSON:
    - `workflow_id`, `next_action` (ask_clarifying|call_tool|respond|escalate)
    - `required_fields_missing[]`
    - `policy_applied[]`
    - `tool_plan[]` (only when `call_tool`)
  - **CRITICAL**: Policy decisions are deterministic, NOT LLM

- [ ] **Orchestrator integration** (1 saat)
  - Orchestrator → WorkflowEngine call
  - Support workflow → tool → workflow → reply loop

- [ ] **Test Gate: WorkflowEngine** (30dk)
  - 10 decision table tests

---

#### Dev B - ToolsClient + Official Tool Integration
**Süre**: 4 saat

- [ ] **Tool Catalog with Official Handles** (1.5 saat)
  - `tools/catalog.json` with official Shopify/Skio handles:
    - tool handle → endpoint → paramsJsonSchema → description
  - Map use-case tools:
    - WISMO: `shopify_get_order_details`, `shopify_get_customer_orders`
    - Wrong/Missing: `shopify_create_return`, `shopify_create_store_credit`
    - Refund: `shopify_refund_order`, `shopify_create_store_credit`

- [ ] **ToolsClient wrapper (CRITICAL)** (1.5 saat)
  - Single entry: `ToolsClient.execute(tool_handle, params)`
  - **JSON-Schema validation** on params BEFORE calling
  - Enforce HTTP 200 + `{success, data?, error?}` contract
  - Normalize all responses
  - 1 retry on transient failure → escalation if still fails
  - Log every call to trace: `{tool_handle, params, response, success, retry_count, timestamp}`

- [ ] **Mock Tool Server** (1 saat)
  - Local stubs returning official contract format
  - Support success/failure scenarios for testing

**⚠️ Test Gate**:
- [ ] JSON-schema validation rejects invalid params
- [ ] success:false → retry=1 → escalation flag
- [ ] Trace contains tool_call events with input/output

---

## 📅 Gün 2 - Tamamlama + Demo Hazırlığı

### Sabah (09:00 - 13:00) - **4 saat**

#### Dev A - Support Agent + Escalation Agent
**Süre**: 3.5 saat

- [ ] **Support/Response Agent** (2 saat)
  - Prompt: workflow decision + tool result → customer email
  - Brand tone: empathetic, professional, clear
  - Output: email subject + body
  - Include confirmation for any actions taken
  
- [ ] **Escalation Agent** (1.5 saat)
  - Triggers: policy exception, tool fail (after retry), confidence < 0.6
  - Customer message: "Your request has been escalated to our specialist team. You'll receive a response within 24 hours."
  - **Internal team JSON (REQUIRED SCHEMA)**:
    ```json
    {
      "escalation_id": "esc_xxx",
      "customer_id": "cust_XXXXXXXX",
      "reason": "string",
      "conversation_summary": "string",
      "attempted_actions": ["array"],
      "priority": "low|medium|high",
      "created_at": "ISO-8601"
    }
    ```
  - Set session status = "escalated" (SESSION LOCK)
  - **Stop automatic answer generation** for rest of session

**⚠️ Test Gate**: 
- [ ] Escalation JSON schema validation
- [ ] Session lock: escalated session rejects new auto-replies

---

#### Dev B - Workflow JSONs + Ticket Infrastructure
**Süre**: 3.5 saat

> **Ownership**: `workflows/` JSON files owned by Dev B

- [ ] **WISMO workflow JSON** (45dk)
  - Use official tools: `shopify_get_order_details`
  - Mon–Wed: Friday promise
  - Thu–Sun: Early next week promise
  - Post-promise not delivered → escalate

- [ ] **Wrong/Missing Item workflow JSON** (1 saat)
  - Use official tools: `shopify_create_return`, `shopify_create_store_credit`, `shopify_refund_order`
  - Request evidence: item photo + packing slip + shipping label
  - Priority: reship (escalate) → store credit (+10%) → cash refund
  - Evidence missing → ask_clarifying

- [ ] **Refund Standard workflow JSON** (1 saat)
  - Use official tools: `shopify_refund_order`, `shopify_create_store_credit`
  - Reason = shipping delay → route to WISMO
  - Reason = wrong/missing → route to WRONG_MISSING
  - Unclear reason → ask_clarifying or escalate

- [ ] **TicketStore Interface + Fixtures** (45dk)
  - Create `TicketStore` interface (abstract)
  - Create `DummyTicketStore` with fixture tickets
  - Prepare parser for tomorrow's real ticket ingestion

**⚠️ Test Gate**: 
- [ ] Each workflow: 3+ fixtures (input → expected action + policy)
- [ ] TicketStore interface works with dummy data

---

### Öğle Arası (13:00 - 14:00)

---

### Öğleden Sonra (14:00 - 18:00) - **4 saat**

#### Birlikte - Testing + Demo Hazırlığı

**14:00 - 15:30 (1.5 saat) - Senaryo Testleri**
- [ ] Run all demo scenarios
- [ ] Record trace output for each
- [ ] Test edge cases:
  - Missing order_id
  - Ambiguous intent
  - Tool failure
  - Escalation trigger

**15:30 - 16:30 (1 saat) - Observability Audit**
- [ ] Verify `/trace` output contains:
  - [ ] Final customer message
  - [ ] All tools called (with inputs/outputs)
  - [ ] All actions taken
  - [ ] Agent decision timeline
  - [ ] Escalation reasons (if any)
- [ ] (Bonus) Simple HTML trace viewer

**16:30 - 17:30 (1 saat) - Demo Rehearsal**
- [ ] 3 use-case demo flows
- [ ] Pre-recorded backup
- [ ] Presentation order:
  1. System architecture (5min)
  2. WISMO scenario live (3min)
  3. Wrong/Missing scenario (3min)
  4. Trace visualization (2min)
  5. Escalation example (2min)

**17:30 - 18:00 (30dk) - Polish**
- [ ] README.md (setup, endpoints, architecture)
- [ ] Code cleanup
- [ ] .env.example check
- [ ] Final test run

---

## 👁️ Observability Requirements (Per Session)

**MUST be inspectable via `/trace` or logs:**

| Item | Description |
|------|-------------|
| **Final Customer Message** | Last reply sent to customer |
| **Tools Called** | List of tool handles with inputs/outputs |
| **Actions Taken** | Any state changes (refund issued, credit created, etc.) |
| **Agent Decision Timeline** | Sequence: triage → workflow → action → support |
| **Escalation Details** | Reason, summary, priority (if escalated) |

**Trace Event Schema:**
```json
{
  "session_id": "xxx",
  "events": [
    {
      "agent": "triage|workflow|action|support|escalation",
      "action": "classify|decide|call_tool|respond|escalate",
      "data": {...},
      "timestamp": "ISO-8601"
    }
  ]
}
```

---

## 📋 Step Completion Note Template

**CRITICAL**: Use this template after every major task.

```markdown
✅ Step Completion Note

**Step name**: [e.g., "Orchestrator logic"]

**Implemented:**
- [ ] Files/functions/endpoints created
- [ ] Schemas defined
- [ ] Integration points

**Key Decisions:**
- [ ] Why this approach was chosen

**Interfaces/Contracts:**
- [ ] Input/output schemas
- [ ] Dependencies on other modules

**How it connects to other modules:**
- [ ] What calls this, what this calls

**Tests executed (with results):**
- [ ] Unit: [✓/✗] test name
- [ ] Integration: [✓/✗] test name
- [ ] Use-case ref: which scenario tested

**Trace sample (1-2 events):**
```json
{
  "agent": "triage",
  "action": "classify",
  "data": {"intent": "WISMO", "confidence": 0.92}
}
```

**Remaining risks / TODO:**
- [ ] Known limitations
```

---

## ✅ Definition of Done (Evaluation Dimensions)

### 1. Workflow Correctness
- [ ] Deterministic workflow engine (no LLM policy decisions)
- [ ] Policy boundaries enforced
- [ ] Multi-message consistency (no contradictions)
- [ ] All use-case PDF rules implemented

### 2. Tool Use Quality
- [ ] Correct tool selection per scenario
- [ ] Correct params (validated against JSON schema)
- [ ] Minimal tool calls (no redundant calls)
- [ ] Handle `success:false` gracefully (retry → escalate)
- [ ] Map tool results to customer replies accurately

### 3. Customer Experience
- [ ] Clear, safe tone in all replies
- [ ] Confirmations for any actions taken
- [ ] No policy hallucinations
- [ ] Professional email format

### 4. Escalation Behavior
- [ ] Correct triggers (policy exception, tool fail, low confidence)
- [ ] Customer message: "Escalated to specialist team"
- [ ] Structured team summary (required JSON schema)
- [ ] Session lock (no more auto-replies after escalation)

---

## 🧪 Test Plan

### A) Smoke Tests
- [ ] `POST /session/start` → 200 + session_id
- [ ] `POST /session/{id}/message` → 200 + response
- [ ] `GET /session/{id}/trace` → JSON timeline

### B) Unit Tests
**SessionStore:**
- [ ] Create/get/update operations
- [ ] Session lock prevents new messages

**WorkflowEngine:**
- [ ] WISMO: Mon-Wed → Friday promise
- [ ] Wrong/Missing: evidence missing → ask_clarifying
- [ ] Refund: shipping delay → route to WISMO

**ToolsClient:**
- [ ] JSON-schema validation on params
- [ ] Retry logic
- [ ] Trace logging

### C) Integration Tests
- [ ] Full flow: message → triage → workflow → action → support
- [ ] Tool failure → escalation → session lock
- [ ] Escalation JSON schema validated

### D) Use-Case Tests
**Test 1 - WISMO:**
```json
{
  "input": "Where is my order #12345?",
  "expected": {
    "intent": "WISMO",
    "tools_called": ["shopify_get_order_details"],
    "policy_applied": "friday_promise"
  }
}
```

**Test 2 - Wrong/Missing:**
```json
{
  "input": "I'm missing an item from my order",
  "expected": {
    "intent": "WRONG_MISSING",
    "action": "ask_clarifying",
    "evidence_requested": ["item_photo", "packing_slip", "shipping_label"]
  }
}
```

**Test 3 - Refund:**
```json
{
  "input": "I want a refund, shipping was too slow",
  "expected": {
    "intent": "REFUND_STANDARD",
    "routed_to": "WISMO"
  }
}
```

---

## 📊 Risk Yönetimi

| Risk | Olasılık | Etki | Mitigation |
|------|----------|------|------------|
| **Policy hallucination** | **Yüksek** | **Kritik** | **Workflow JSON deterministic** |
| LLM response slow | Yüksek | Orta | Async + 10s timeout |
| Tool API fail | Orta | Yüksek | Mock fallback + retry |
| Ticket format mismatch | Düşük | Orta | Parser validates format |
| Demo crash | Düşük | Kritik | Pre-recorded backup |

---

## ⚠️ CRITICAL WARNINGS

### 1. Policy Hallucination - P0 Risk
❌ **DON'T**: Let LLM make policy decisions
✅ **DO**: Workflow JSON deterministic, LLM only renders text

### 2. Official Tool Handles
❌ **DON'T**: Use generic tool names like `check_order_status`
✅ **DO**: Use official handles: `shopify_get_order_details`, etc.

### 3. Escalation JSON Schema
❌ **DON'T**: Free-form escalation JSON
✅ **DO**: Use required schema with all fields

### 4. JSON-Schema Validation
❌ **DON'T**: Call tools without validating params
✅ **DO**: Validate against paramsJsonSchema BEFORE calling

### 5. Session Lock
❌ **DON'T**: Allow auto-replies after escalation
✅ **DO**: Lock session, stop automation

---

## 🎯 Sprint Success Criteria

- [ ] 3 use-cases working (WISMO, Refund, Wrong Item)
- [ ] Escalation triggers correctly + session locks
- [ ] Trace shows all decisions/tools/actions
- [ ] Official tool handles used
- [ ] JSON-schema validation on params
- [ ] Demo runs smoothly
- [ ] Ticket ingestion ready for tomorrow

**Başarılar! 🚀**
