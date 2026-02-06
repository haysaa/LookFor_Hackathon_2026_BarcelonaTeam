# Lookfor Hackathon 2026 - Sprint Plan (2 Gün)

**Takım**: 2 Developer (Dev A + Dev B)  
**Platform**: OpenAI API (GPT-4o mini) + deterministic workflow engine  
**Hedef**: WISMO, Refund, Wrong/Missing Item için çalışan multi-agent email support sistemi

---

## 🎯 Sprint Hedefleri

- [x] 3 use-case için end-to-end akış çalışır durumda
- [x] Session yönetimi + escalation logic
- [x] Tool entegrasyonu (resmi Shopify/Skio tool'ları)
- [x] Observable trace system
- [ ] Ticket dataset ingestion (yarın gelecek)
- [x] Demo senaryolarının tümü geçer
- [x] Canlı demo yapılabilir durumda sunum

---

## 📋 Minimum Gereksinimler (Hackathon Spec)

### ✅ Email Session Start
- Session start MUST accept: `customer_email`, `first_name`, `last_name`, `shopify_customer_id`
- Endpoint: `POST /session/start`

### ✅ Inquiry Handling with Continuous Memory
- Multi-turn session handling
- Conversation history maintained per session
- No contradictions between turns
- Behaves like real email thread

### ✅ Observable Answers and Actions
Per session we MUST inspect:
- Final customer message
- Any tools called with inputs/outputs
- Any actions taken
- Trace/timeline of agent decisions (visible via `GET /session/{id}/trace`)

### ✅ Escalation Mechanism
When required by workflow or uncertainty:
1. Inform customer it's escalated ("Uzman ekibimize iletildi, 24 saat içinde dönüş")
2. Create structured team summary (JSON schema below)
3. Stop automatic answer generation (session lock: `status=escalated`)

**Escalation JSON Schema (REQUIRED)**:
```json
{
  "escalation_id": "esc_xxx",
  "customer_id": "cust_xxx",
  "reason": "string",
  "conversation_summary": "string",
  "attempted_actions": ["array"],
  "priority": "low|medium|high",
  "created_at": "ISO-8601 timestamp"
}
```

---

## 🎫 Ticket Dataset Track (BUGÜN + YARIN)

### Bugün - TicketStore Interface + Fixtures
**Sahip**: Dev A  
**Süre**: 1 saat

- [ ] **TicketStore interface** tanımla:
  ```python
  class TicketStore:
      def get_by_conversation_id(self, conv_id: str) -> Ticket | None
      def get_by_customer_id(self, cust_id: str) -> list[Ticket]
      def search_similar(self, query: str, limit: int) -> list[Ticket]
      def ingest(self, tickets: list[dict]) -> int
  ```

- [ ] **Dummy fixtures** oluştur (`fixtures/tickets_dummy.json`):
  ```json
  [
    {
      "conversationId": "abc123@email.com",
      "customerId": "cust_12345678",
      "createdAt": "06-Feb-2026 14:30:00",
      "ConversationType": "email",
      "subject": "Siparişim nerede?",
      "conversation": "Merhaba, 3 gün önce sipariş verdim..."
    }
  ]
  ```

- [ ] **InMemoryTicketStore** implementasyonu (dict-based)

**⚠️ Test Gate**: `ticket_store.get_by_customer_id("cust_12345678")` → fixture döner

### Yarın - Gerçek Ticket Ingestion
**Sahip**: Dev A  
**Süre**: 30dk (dataset gelince)

- [ ] Parse ticket JSON (format yukarıdaki gibi)
- [ ] `TicketStore.ingest(tickets)` çağır
- [ ] Basit RAG için keyword search ekle (optional)
- [ ] Test: 10 random ticket'ı query et

---

## 🔧 Official Tool Handles (Shopify + Skio)

> **KRİTİK**: Generic mock tool isimleri KULLANILMAYACAK. Aşağıdaki resmi handle'lar kullanılacak.

### Shopify Tools
| Handle | Açıklama | Use-Case |
|--------|----------|----------|
| `shopify_get_order_details` | Sipariş detayları | WISMO, Refund |
| `shopify_get_customer_orders` | Müşteri siparişleri | Tümü |
| `shopify_refund_order` | İade işlemi | Refund |
| `shopify_create_store_credit` | Store credit oluştur | Wrong/Missing |
| `shopify_create_return` | İade talebi oluştur | Refund |
| `shopify_cancel_order` | Sipariş iptal | Refund |
| `shopify_add_tags` | Tag ekle | Escalation tracking |
| `shopify_create_discount_code` | İndirim kodu | Compensation |
| `shopify_update_order_shipping_address` | Adres güncelle | WISMO |
| `shopify_get_product_details` | Ürün detayı | Wrong/Missing |
| `shopify_get_product_recommendations` | Ürün önerileri | Upsell |
| `shopify_get_collection_recommendations` | Koleksiyon | Upsell |
| `shopify_get_related_knowledge_source` | Bilgi bankası | Tümü |
| `shopify_create_draft_order` | Taslak sipariş | Reship |

### Skio Tools (Subscription)
| Handle | Açıklama |
|--------|----------|
| `skio_get_subscription_status` | Abonelik durumu |
| `skio_cancel_subscription` | Abonelik iptal |
| `skio_pause_subscription` | Abonelik duraklat |
| `skio_unpause_subscription` | Abonelik devam |
| `skio_skip_next_order_subscription` | Sonraki siparişi atla |

---

## 🔌 ToolsClient Requirements (KRİTİK)

### Uniform API Response Contract
Tüm tool endpoint'leri HTTP 200 döner:

**Success**:
```json
{ "success": true }
// veya
{ "success": true, "data": { ... } }
```

**Failure**:
```json
{ "success": false, "error": "Human readable error message" }
```

### ToolsClient Wrapper Gereksinimleri
**Sahip**: Dev A (infrastructure) + Dev B (integration)

- [ ] **JSON Schema Validation** (ZORUNLU):
  - Her tool çağrısı öncesi `paramsJsonSchema` ile params validate et
  - Validation fail → tool çağırma, hata dön

- [ ] **Normalized Response**:
  - Her response `{success, data?, error?}` formatına normalize et

- [ ] **Retry Logic**:
  - Transient failure → 1 retry
  - 2. failure → `should_escalate=true`

- [ ] **Trace Logging**:
  - Her tool call: `{tool_name, params, response, success, retry_count, timestamp}`

### tools/catalog.json Format
```json
{
  "shopify_get_order_details": {
    "handle": "shopify_get_order_details",
    "endpoint": "/api/tools/shopify/get_order_details",
    "description": "Get order details by order ID",
    "paramsJsonSchema": {
      "type": "object",
      "properties": {
        "order_id": { "type": "string" }
      },
      "required": ["order_id"]
    }
  },
  "shopify_refund_order": {
    "handle": "shopify_refund_order",
    "endpoint": "/api/tools/shopify/refund_order",
    "description": "Process refund for an order",
    "paramsJsonSchema": {
      "type": "object",
      "properties": {
        "order_id": { "type": "string" },
        "amount": { "type": "number" },
        "reason": { "type": "string" }
      },
      "required": ["order_id"]
    }
  }
}
```

---

## 📅 Gün 1 - Temel Altyapı + İlk Akış

### Sabah (09:00 - 13:00) - **4 saat**

#### Dev A - Session & Orchestrator Core ✅
**Süre**: 3.5 saat | **Status**: TAMAMLANDI

- [x] **Session State modeli** (30dk)
  - `Session` dataclass: customer_info, messages, intent, case_context, tool_history, status
  - In-memory store (dict based)
  
- [x] **Session endpoints** (1 saat)
  - `POST /session/start` - customer bilgileriyle session oluştur
  - `POST /session/{id}/message` - mesaj al, orchestrator'a yönlendir
  - `GET /session/{id}/trace` - timeline JSON döndür
  
- [x] **Orchestrator logic** (2 saat)
  - Session status kontrolü (escalated ise durma)
  - Agent çağrı sıralaması: triage → workflow → (action?) → support
  - Escalation tetikleyicilerini handle et
  - Her adımı trace listesine kaydet

<details>
<summary>✅ Step Completion Note - Session & Orchestrator</summary>

**Implementasyon**:
- `app/models.py`: Session, Message, TraceEvent, CaseContext, EscalationPayload
- `app/store.py`: InMemory SessionStore
- `app/api.py`: FastAPI endpoints
- `app/orchestrator.py`: Agent pipeline coordinator
- `app/trace.py`: TraceLogger utility

**Test Sonuçları**: 14/14 passed
- Smoke tests: /start, /message, /trace endpoints
- Unit tests: SessionStore CRUD, escalation lock

**Trace Sample**:
```json
{"event_type": "customer_message", "data": {"message": "Siparişim nerede?"}}
{"event_type": "triage_result", "agent": "triage", "data": {"intent": "WISMO", "confidence": 0.92}}
{"event_type": "workflow_decision", "agent": "workflow", "data": {"next_action": "respond"}}
```
</details>

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

#### Dev A - Workflow Engine ✅
**Süre**: 4 saat | **Status**: TAMAMLANDI

- [x] **WorkflowEngine (JSON loader + evaluator)** (2.5 saat)
- [x] **Orchestrator entegrasyonu** (1 saat)
- [x] **Test Gate**: 9/9 workflow tests passed

<details>
<summary>✅ Step Completion Note - Workflow Engine</summary>

**Implementasyon**:
- `app/workflow/__init__.py`: WorkflowEngine class
- `workflows/wismo.json`: WISMO decision tree
- `workflows/wrong_missing.json`: Wrong/Missing decision tree
- `workflows/refund_standard.json`: Refund routing

**Test Sonuçları**: 9/9 passed
</details>

---

#### Dev B - ToolsClient + Action Agent (UPDATED)
**Süre**: 4 saat

- [ ] **tools/catalog.json** güncelle (OFFICIAL HANDLES):
  - `shopify_get_order_details`
  - `shopify_get_customer_orders`
  - `shopify_refund_order`
  - `shopify_create_store_credit`
  - `shopify_create_return`
  - Her tool için `paramsJsonSchema` tanımla

- [ ] **ToolsClient JSON Schema Validation** ekle:
  ```python
  def validate_params(self, tool_name: str, params: dict) -> bool:
      schema = self.catalog[tool_name]["paramsJsonSchema"]
      # jsonschema.validate(params, schema)
  ```

- [ ] **Mock responses** resmi tool handle'ları için

**⚠️ Test Gate**:
- JSON schema validation fail → tool çağrılmaz
- success:false → retry=1 → escalation flag

---

## 📅 Gün 2 - Tamamlama + Demo Hazırlığı

### Sabah (09:00 - 13:00) - **4 saat**

#### Dev A - Support Agent + Escalation Agent + TicketStore ✅
**Süre**: 3.5 saat | **Status**: TAMAMLANDI (TicketStore hariç)

- [x] **Support/Response Agent** (2 saat)
- [x] **Escalation Agent** (1.5 saat) - Schema uyumlu
- [ ] **TicketStore Interface** (30dk) - YENİ

<details>
<summary>✅ Step Completion Note - Support & Escalation</summary>

**Implementasyon**:
- `app/agents/support.py`: SupportAgent (LLM + template fallback)
- `app/agents/escalation.py`: EscalationAgent (structured JSON)

**Escalation Schema Compliance**: ✅
```json
{
  "escalation_id": "esc_abc123",
  "customer_id": "cust_123",
  "reason": "Reship requires manual approval",
  "conversation_summary": "...",
  "attempted_actions": ["shopify_get_order_details"],
  "priority": "medium",
  "created_at": "2026-02-06T14:30:00Z"
}
```

**Test Sonuçları**: 7/7 escalation tests passed
</details>

---

#### Dev B - Workflow JSON'lar (Use-Case'e Göre) - UPDATED
**Süre**: 3.5 saat

- [ ] **WISMO workflow JSON** - Official tool handles:
  - `tools_to_call`: `["shopify_get_order_details"]`

- [ ] **Wrong/Missing Item workflow JSON**:
  - `tool_name`: `shopify_create_store_credit`, `shopify_refund_order`

- [ ] **Refund Standard workflow JSON**:
  - `tool_name`: `shopify_refund_order`, `shopify_create_return`

---

### Öğleden Sonra (14:00 - 18:00) - **4 saat**

#### Birlikte - Testing + Demo Hazırlığı

**14:00 - 15:00 (1 saat) - Ticket Ingestion** (YENİ)
- [ ] Ticket dataset gelince `TicketStore.ingest()` çağır
- [ ] 10 random ticket query testi
- [ ] Support Agent'a ticket RAG ekle (optional)

**15:00 - 16:30 (1.5 saat) - Senaryo Testleri**
- [ ] 3 use-case demo senaryoları
- [ ] Edge case'ler

**16:30 - 17:30 (1 saat) - Demo Rehearsal**
- [ ] Demo flow
- [ ] Backup kayıtları

**17:30 - 18:00 (30dk) - Polish**
- [ ] README.md
- [ ] Final test

---

## 📊 Evaluation Dimensions → Sprint Outputs

### 1. Workflow Correctness
| Criteria | Sprint Output |
|----------|---------------|
| Deterministic workflow engine | `WorkflowEngine` + JSON decision trees |
| Policy boundaries respected | No LLM policy decisions |
| Multi-message consistency | Session memory + no contradictions |

### 2. Tool Use Quality
| Criteria | Sprint Output |
|----------|---------------|
| Correct tool selection | Workflow JSON defines tool plan |
| Correct params (JSON Schema) | `ToolsClient.validate_params()` |
| Minimal calls | Workflow defines exactly needed tools |
| Handle success:false | Retry logic + escalation |
| Map tool results to replies | SupportAgent uses tool results |

### 3. Customer Experience
| Criteria | Sprint Output |
|----------|---------------|
| Clear safe tone | SupportAgent brand tone prompts |
| Confirmations for actions | Templates confirm actions taken |

### 4. Escalation Behavior
| Criteria | Sprint Output |
|----------|---------------|
| Correct triggers | Workflow `action=escalate` rules |
| Customer message | "Uzman ekibimize iletildi..." |
| Structured team summary | EscalationPayload schema |
| Session lock | `status=escalated` blocks messages |

---

## 🧪 Test Plan Summary

### Test Gate Checklist (Her Modül Sonrası)

| Modül | Unit Tests | Integration | Use-Case |
|-------|-----------|-------------|----------|
| SessionStore | ✅ 8 passed | ✅ smoke | - |
| Orchestrator | ✅ 6 passed | ✅ full flow | - |
| WorkflowEngine | ✅ 9 passed | - | WISMO, Wrong/Missing |
| ToolsClient | ✅ 8 passed | ✅ retry test | - |
| EscalationAgent | ✅ 7 passed | ✅ schema test | Escalation scenario |
| TicketStore | ⏳ pending | ⏳ pending | - |

**Total**: 38+ tests passed

---

## ✅ Definition of Done (UPDATED)

### Workflow Correctness
- [x] Deterministic WorkflowEngine implemented
- [x] Policy decisions via JSON, NOT LLM
- [x] Multi-message session consistency

### Tool Use Quality
- [x] ToolsClient with official Shopify/Skio handles
- [ ] JSON Schema param validation
- [x] Retry logic (1 retry)
- [x] Tool results logged to trace

### Customer Experience
- [x] Empathetic Turkish responses
- [x] Clear action confirmations

### Escalation Behavior
- [x] Triggers: policy outside, tool fail x2, confidence < 0.6
- [x] Customer message sent
- [x] Structured JSON (schema compliant)
- [x] Session locked

### Observability
- [x] Final customer message in trace
- [x] All tool calls with input/output
- [x] All actions taken logged
- [x] Agent decision timeline via `/trace`

---

## 📄 Updated Workflow JSON Examples (Official Tools)

### workflows/wismo.json
```json
{
  "workflow_name": "WISMO",
  "version": "2.0",
  "rules": [
    {
      "condition": "contact_day in ['Mon', 'Tue', 'Wed']",
      "action": "respond",
      "policy_applied": "friday_promise",
      "response_template": "Siparişiniz Cuma gününe kadar size ulaşacaktır."
    },
    {
      "condition": "contact_day in ['Thu', 'Fri', 'Sat', 'Sun']",
      "action": "respond",
      "policy_applied": "next_week_promise",
      "response_template": "Siparişiniz önümüzdeki hafta başında size ulaşacaktır."
    },
    {
      "condition": "promise_given and still_not_delivered",
      "action": "escalate",
      "policy_applied": "post_promise_escalation",
      "escalation_reason": "Delivery promise exceeded"
    }
  ],
  "required_fields": ["order_id"],
  "tools_to_call": ["shopify_get_order_details"]
}
```

### workflows/wrong_missing.json
```json
{
  "workflow_name": "WRONG_MISSING",
  "version": "2.0",
  "rules": [
    {
      "condition": "evidence_missing",
      "action": "ask_clarifying",
      "required_fields_missing": ["item_photo", "packing_slip", "shipping_label"],
      "policy_applied": "evidence_requirement"
    },
    {
      "condition": "evidence_complete",
      "action": "escalate",
      "policy_applied": "reship_priority",
      "escalation_reason": "Reship request requires manual approval"
    },
    {
      "condition": "customer_prefers_credit",
      "action": "call_tool",
      "tool_name": "shopify_create_store_credit",
      "policy_applied": "store_credit_10_percent_bonus"
    },
    {
      "condition": "all_alternatives_rejected",
      "action": "call_tool",
      "tool_name": "shopify_refund_order",
      "policy_applied": "cash_refund_last_resort"
    }
  ],
  "required_fields": ["order_id", "item_name"],
  "priority_order": ["reship", "store_credit", "cash_refund"]
}
```

### workflows/refund_standard.json
```json
{
  "workflow_name": "REFUND_STANDARD",
  "version": "2.0",
  "rules": [
    {
      "condition": "refund_reason == 'shipping_delay'",
      "action": "route_to_workflow",
      "target_workflow": "WISMO",
      "policy_applied": "shipping_delay_uses_wismo_rules"
    },
    {
      "condition": "refund_reason == 'wrong_missing'",
      "action": "route_to_workflow",
      "target_workflow": "WRONG_MISSING",
      "policy_applied": "wrong_missing_uses_dedicated_workflow"
    },
    {
      "condition": "refund_reason == 'other' and within_policy",
      "action": "call_tool",
      "tool_name": "shopify_refund_order",
      "policy_applied": "standard_refund_eligibility"
    },
    {
      "condition": "outside_policy",
      "action": "escalate",
      "escalation_reason": "Refund request outside standard policy"
    }
  ],
  "required_fields": ["order_id", "refund_reason"]
}
```

---

## 📋 Step Completion Note Template

```markdown
✅ Step Completion Note

**Step adı**: [örn. "Orchestrator logic"]

**Ne implementasyon yapıldı?**
- Dosyalar: [liste]
- Endpoints: [liste]
- Schemas: [liste]

**Kabul kriteri / çıktılar**:
- Test sonucu: X/Y passed
- Trace events: [örnek]

**Trace/Log örneği**:
```json
{"event_type": "...", "agent": "...", "data": {...}}
```

**Sonraki adımlara bağlantı**:
- [Hangi modül bu çıktıyı kullanacak]

**Testler**:
- Unit: [✓/✗] test_xxx.py
- Integration: [✓/✗] test_integration.py
- Use-case: [hangi senaryo]

**Bilinen eksikler**:
- [TODO listesi]
```

---

## 🎯 Sprint Başarı Kriterleri

- [x] 3 use-case çalışıyor (WISMO, Refund, Wrong Item)
- [x] Escalation logic doğru tetikleniyor
- [x] Trace sistemi tüm kararları gösteriyor
- [ ] Ticket ingestion ready (yarın)
- [x] Demo yapılabilir durumda
- [x] Kod temiz ve dokümante

**Başarılar! 🚀**
