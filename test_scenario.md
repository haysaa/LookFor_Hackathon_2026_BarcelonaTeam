# Test Senaryosu - Hackathon Tool Spec Compliance

## 🎯 Test Hedefi
18 official Hackathon tool'unun doğru çalıştığını ve spec'e uygun response döndüğünü doğrulamak.

---

## ✅ Senaryo 1: Otomatik Tool Test (Önerilen)

### Adımlar:

**1. Test script'ini çalıştır:**
```bash
python test_tools_spec.py
```

**2. Beklenen Çıktı:**
- ✅ 18/18 tool başarılı test edilmeli
- Her tool için `success: true/false` görmeli
- Response formatı spec'e uygun olmalı: `{success, data?, error?}`

**3. Success Kriterleri:**
- Tüm tool'lar exception fırlatmadan çalışmalı
- JSON schema validation geçmeli
- Mock server doğru response dönmeli

---

## 🌐 Senaryo 2: Web UI ile Manuel Test

### Adımlar:

**1. Sunucu çalışıyor mu kontrol et:**
Tarayıcıda: http://localhost:8000

**2. Demo UI'dan bir senaryo test et:**
- WISMO (Where Is My Order)
- Refund Request  
- Wrong/Missing Item

**3. Network tab'dan API çağrılarını incele:**
- Session başlatma: `POST /session/start`
- Mesaj gönderme: `POST /session/{id}/message`
- Trace görüntüleme: `GET /session/{id}/trace`

---

## 🔧 Senaryo 3: API Direct Test (cURL)

### Test 1: Session Başlat
```bash
curl -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -d "{\"use_case\": \"wismo\", \"customer_query\": \"Where is my order #1234?\"}"
```

**Beklenen Response:**
```json
{
  "session_id": "...",
  "status": "...",
  "message": "..."
}
```

### Test 2: Mesaj Gönder
```bash
# Session ID'yi yukarıdaki response'dan al
curl -X POST http://localhost:8000/session/{SESSION_ID}/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"My order number is #1234\"}"
```

### Test 3: Trace Kontrol
```bash
curl http://localhost:8000/session/{SESSION_ID}/trace
```

**Kontrol edilecekler:**
- Tool execution trace'leri var mı?
- Her tool call için `success: true/false` mevcut mu?
- Error mesajları anlamlı mı?

---

## 🧪 Senaryo 4: Specific Tool Test (Python Console)

Terminal'de:
```bash
python
```

Sonra:
```python
from tools.client import ToolsClient

# Mock server ile client oluştur
client = ToolsClient(use_mock=True)

# Test 1: Order Details
result = client.execute(
    "shopify_get_order_details",
    {"orderId": "#1234"}
)
print(f"Success: {result.success}")
print(f"Data: {result.data}")

# Test 2: Subscription Status
result = client.execute(
    "skio_get_subscription_status",
    {"email": "test@example.com"}
)
print(f"Success: {result.success}")
print(f"Data: {result.data}")

# Test 3: Invalid params (should fail validation)
result = client.execute(
    "shopify_add_tags",
    {"wrong_param": "value"}  # Missing required fields
)
print(f"Success: {result.success}")
print(f"Error: {result.error}")  # Should show validation error
```

---

## ✅ Beklenen Sonuçlar

### Tool Count
- ✅ Exactly 18 tools in catalog
- ✅ 13 Shopify tools
- ✅ 5 Skio tools

### Response Format (Her tool için)
```json
{
  "success": true/false,
  "data": {...},      // Optional, only on success
  "error": "..."      // Optional, only on failure
}
```

### Schema Validation
- ✅ Invalid params rejected before API call
- ✅ Clear validation error messages
- ✅ Required fields enforced

### Endpoints
- ✅ All use pattern: `{API_URL}/hackathon/{endpoint_name}`
- ✅ All use POST method
- ✅ All accept JSON body

---

## 🐛 Sorun Giderme

### Test başarısız olursa:

**1. Import hatası:**
```bash
# Python path ekle
set PYTHONPATH=c:\Users\kmndm\Masaüstü\LookFor_Hackathon_2026_BarcelonaTeam
python test_tools_spec.py
```

**2. Sunucu çalışmıyor:**
```bash
# Yeni terminal'de
cd c:\Users\kmndm\Masaüstü\LookFor_Hackathon_2026_BarcelonaTeam
python main.py
```

**3. Mock server hatası:**
Test script'te `use_mock=True` olduğundan emin ol.

---

## 📊 Success Metrics

Başarılı test için:
- [x] ✅ 18/18 tool test edildi
- [x] ✅ Tüm tool'lar exception fırlatmadan çalıştı
- [x] ✅ Schema validation çalışıyor
- [x] ✅ Response format spec'e uygun
- [x] ✅ Error handling doğru
