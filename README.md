# 🚀 LookFor Hackathon 2026 – BarcelonaTeam

Multi-Agent Customer Support System for automated resolution of WISMO (Where Is My Order), Refund, and Wrong / Missing Item use cases.

Built with LLM-based intent detection, structured workflow orchestration, deterministic business rules, escalation control, full session trace logging, and Docker-based reproducibility.

---

## 🧠 Problem

E-commerce platforms receive thousands of repetitive support tickets daily:

- “Where is my order?”
- “I want a refund.”
- “I received the wrong item.”

Manual handling leads to high operational costs, inconsistent decisions, delayed responses, and lack of traceability.

Most AI chatbot systems either:
- Answer vaguely,
- Or make uncontrolled decisions,
- Or lack auditability.

We wanted to build something closer to enterprise-grade customer operations automation.

---

## 💡 Solution

We built a multi-agent orchestration system that:

- Detects customer intent using an LLM
- Routes requests to the correct domain agent
- Applies structured, deterministic business rules
- Enforces delivery promises
- Automatically escalates when SLAs are violated
- Stores full session trace for auditability and debugging

This is not a generic chatbot.  
It is a controllable AI-assisted customer support engine.

---

## 🏗 Architecture Overview

The system consists of:

- 🎯 Intent Agent (LLM-based classification)
- 📦 WISMO Agent
- 💸 Refund Agent
- 📦❌ Wrong / Missing Item Agent
- 🧠 Orchestrator (routing and control layer)
- 📚 Ticket Store (dummy or real anonymized tickets)
- 📊 Session Trace Manager

Each request follows this lifecycle:

1. Session is started
2. User message is received
3. Intent is detected
4. Orchestrator routes to relevant agent
5. Agent executes structured workflow
6. Business rules applied
7. Trace updated
8. Response returned

All state transitions are logged.

---

## 🔄 Complete Workflow Coverage

### 📦 WISMO – Where Is My Order

WISMO includes delivery promise logic based on day-of-week rules.

### Promise Rules

| Customer Contacts | Promise | Deadline |
|-------------------|---------|----------|
| Mon–Wed | "by Friday" | Friday of current week |
| Thu–Sun | "early next week" | Next Monday |

### Session Context Fields

- `wismo_promise_type`
- `wismo_promise_deadline`
- `wismo_promise_set_at`

### Escalation Logic

If customer contacts again **after the promised deadline** and order is still not delivered:

- Escalation is triggered
- Escalation reason is logged
- Session is locked
- No further automated replies are allowed

This simulates real SLA enforcement.

---

### 💸 Refund Flow

Refund logic includes:

- Order validation
- Shipment status check
- Conditional refund approval
- If order is shipped → guide customer to return process
- If wrong or missing item → redirect to resolution workflow
- Controlled, rule-based responses

No blind LLM decisions are allowed in financial logic.

---

### 📦❌ Wrong / Missing Item Flow

This workflow:

- Collects reason from customer
- Validates order
- Suggests structured resolution
- Escalates when necessary
- Logs all state transitions

---

## 📊 Observability & Auditability

Each session stores:

- Intent classification
- Agent decisions
- Promise metadata
- Escalation reasons
- Workflow timestamps
- Full conversation history

Trace endpoint:


This ensures:

- Debuggability
- Audit readiness
- Enterprise traceability
- Controlled AI usage

---

## 🖥 Demo Screenshots

### Refund Flow Example

Customer requests refund → Order validation → Shipment logic → Structured response.

![Refund Flow](docs/refund_flow.png)

---

### Order Details Retrieval Example

Intent detection → Order lookup → Structured order summary.

![Order Details](docs/order_details.png)

---

## 🐳 Docker Support

Designed for reproducible evaluation.

Run with Docker:

```bash
docker compose up --build
