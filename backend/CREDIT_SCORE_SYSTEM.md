# Credit Score Pre-Filter System

## Overview

The underwriting backend now includes a **deterministic credit score simulation** system that mimics real CIBIL bureau behavior. Credit scores are tied to PAN numbers, ensuring the same PAN always produces the same score for demo predictability.

**Key Point**: No CIBIL API integration needed for MVP—score derived from PAN via SHA256 hashing.

---

## Credit Score Simulation

### Deterministic Generation

Credit scores are generated deterministically from PAN numbers using SHA256 hashing:

```python
def simulate_credit_score(pan: str) -> int:
    import hashlib
    
    # Validate PAN format: ABCDE1234F
    if not re.match(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', pan):
        raise ValueError("Invalid PAN format")
    
    # Generate deterministic score from PAN hash
    hash_val = int(hashlib.sha256(pan.encode()).hexdigest(), 16)
    
    # Map to 300-900 range (realistic CIBIL range)
    raw_score = 300 + (hash_val % 601)
    return raw_score
```

**Why Deterministic?** Same PAN → Same Score. This mimics real bureau behavior and makes demos predictable.

### Demo PAN Numbers

For easy testing, hardcoded demo scores override simulation:

```python
DEMO_PAN_SCORES = {
    "ABCDE1234F": 820,  # High score — auto-approval
    "XYZPQ5678K": 680,  # Medium score — negotiation allowed
    "LMNOP9012R": 420,  # Low score — high rejection risk
    "QRSTU3456S": 285,  # Below 300 — hard reject
    "DEMO00000D": 750,  # Safe demo score
}
```

**Testing**: Use these PANs to test different paths without worrying about hash variability.

---

## Credit Score Bands

Applicant credit scores determine:
- **Eligibility**: Is loan offered?
- **Interest Rate**: Band + XGBoost combo
- **Negotiation Rounds**: How many times can customer request rate reduction?

### The Five Bands

| Band | Score Range | Label | Color | Eligible? | Rate Range | Negotiation Rounds |
|------|-------------|-------|-------|-----------|------------|-------------------|
| HARD_REJECT | 0–299 | Ineligible | 🔴 Red | ❌ No | — | 0 |
| HIGH_RISK | 300–549 | High Risk | 🟠 Orange | ✅ Yes | 13.5–14% | 0 (fixed rate) |
| MEDIUM_RISK | 550–699 | Medium Risk | 🟡 Yellow | ✅ Yes | 12–13% | 1 round |
| LOW_MEDIUM | 700–749 | Low-Medium Risk | 🟡 Yellow | ✅ Yes | 11.5–12% | 2 rounds |
| LOW_RISK | 750–900 | Low Risk | 🟢 Green | ✅ Yes | 10.5–11.5% | 3 rounds |

### How to Change Bands

Edit `/backend/app/credit_score.py`:

```python
CREDIT_SCORE_BANDS = {
    "HARD_REJECT": {
        "min": 0,
        "max": 299,
        "rate_min": None,  # Not offered
        "rate_max": None,
    },
    # ... other bands
}
```

Change `"max"` to adjust where band boundaries fall.  
Change `"rate_min"` / `"rate_max"` to adjust rate ranges.  
Change `"max_negotiation_rounds"` to allow more/fewer negotiation requests.

---

## New Endpoints

### 1. GET /credit-score/{pan_number}

Called **after KYC verification**, before full /assess.

Returns **credit score, eligibility, and improvement tips** (if rejected).

#### Request
```bash
GET http://localhost:8000/credit-score/ABCDE1234F
```

#### Response (Approved)
```json
{
  "pan_number": "ABCDE****F",
  "credit_score": 820,
  "credit_score_out_of": 900,
  "credit_band": "Low Risk",
  "credit_band_color": "green",
  "eligible_for_loan": true,
  "applicant_score_falls_in": "excellent",
  "message_en": "Great news! Your credit score of 820 qualifies you for our loan products. You fall in the excellent category.",
  "message_hi": "बहुत बढ़िया! आपका credit score 820 है जो हमारे loan products के लिए योग्य है। आप excellent category में आते हैं।",
  "improvement_tips": null,
  "earliest_reapply": null,
  "shortfall": null
}
```

#### Response (Hard Reject)
```json
{
  "pan_number": "QRSTU****S",
  "credit_score": 285,
  "credit_score_out_of": 900,
  "credit_band": "Ineligible",
  "credit_band_color": "red",
  "eligible_for_loan": false,
  "applicant_score_falls_in": "ineligible",
  "message_en": "Your credit score of 285 is below our minimum requirement of 300. You are short by 15 points.",
  "message_hi": "आपका credit score 285 है जो हमारी न्यूनतम आवश्यकता 300 से कम है। आप 15 points से कम हैं।",
  "improvement_tips": [
    "Pay all existing EMIs on time",
    "Clear any outstanding credit card dues",
    "Avoid multiple loan applications in a short period",
    "Maintain credit utilization below 30%",
    "Wait 6 months before reapplying"
  ],
  "earliest_reapply": "6 months from today",
  "shortfall": 15
}
```

**PAN Masking**: Only shows first 5 + last 1 character (ABCDE****F) for privacy.

---

### 2. POST /assess (Updated)

Now includes **PAN number as required field** and applies **credit score pre-filter**.

#### New Request Body Fields
```json
{
  "pan_number": "ABCDE1234F",           // NEW - mandatory
  "preferred_language": "en",            // NEW - default "en"
  "gender": "Male",
  "married": "Yes",
  "dependents": "1",
  "education": "Graduate",
  "self_employed": "No",
  "applicant_income": 5000,
  "coapplicant_income": 1500,
  "loan_amount": 150,
  "loan_amount_term": 360,
  "credit_history": 1,
  "property_area": "Urban"
}
```

#### New Response Fields
```json
{
  "decision": "APPROVED",
  "credit_score": 820,                   // NEW - simulated CIBIL
  "credit_score_out_of": 900,            // NEW
  "credit_band": "Low Risk",             // NEW
  "credit_band_color": "green",          // NEW
  "risk_score": 78,                      // UPDATED - combined score (60% credit + 40% XGBoost)
  "risk_score_out_of": 100,              // NEW
  "approval_probability": 0.85,          // Renamed from approval_probability
  "risk_tier": "Low Risk",
  "offered_rate": 11.0,                  // NEW - determined by credit band
  "rate_range": {                        // NEW
    "min": 10.5,
    "max": 11.5
  },
  "negotiation_allowed": true,           // NEW
  "max_negotiation_rounds": 3,           // NEW - from credit band
  "xgboost_probability": 0.85,           // NEW - raw XGBoost output
  "xgboost_ran": true,                   // NEW - was it executed?
  "shap_explanation": [...],
  "threshold_used": 0.65
}
```

---

## Assessment Flow (with Pre-Filter)

```
1. Frontend calls GET /credit-score/{pan}
   ↓
2. Check score
   ├─ Below 300? → Show rejection, offer improvement tips, END
   └─ >= 300? → Continue step 3
   ↓
3. Frontend calls POST /assess with pan_number
   ↓
4. Backend:
   a. Get credit score from PAN (cached or simulated)
   b. Check band → hard reject if < 300
   c. Run XGBoost model (only if eligible)
   d. Combine scores: 60% credit + 40% XGBoost
   e. Determine final rate from credit band
   f. Set max_negotiation_rounds from band
   ↓
5. Return combined decision + rate + negotiation rounds
   ↓
6. Frontend calls POST /negotiate/start with max_negotiation_rounds
   ↓
7. Negotiation (0–3 rounds based on band)
   ↓
8. POST /negotiate/accept → Sanction letter
```

---

## Negotiation Integration

The negotiation service now accepts `max_negotiation_rounds` from underwriting:

### POST /negotiate/start (Updated)

```json
{
  "applicant_name": "John Doe",
  "risk_score": 78,
  "risk_tier": "Low Risk",
  "loan_amount": 500000,
  "tenure_months": 60,
  "top_positive_factor": "credit history",
  "max_negotiation_rounds": 3          // NEW - from credit band
}
```

The service now uses this value instead of hardcoded `MAX_ROUNDS`, so:
- High Risk customers: 0 rounds (fixed rate)
- Medium Risk: 1 round
- Low Risk: 3 rounds

---

## Configuration

### Changing the Minimum Threshold (Default: 300)

Edit `/backend/app/credit_score.py`:

```python
def simulate_credit_score(pan: str) -> int:
    # Change 300 to your minimum (e.g., 400)
    raw_score = 400 + (hash_val % 500)  # Now 400–900
    return raw_score
```

Update band thresholds too:
```python
CREDIT_SCORE_BANDS = {
    "HARD_REJECT": {
        "min": 0,
        "max": 399,  # Changed from 299
        ...
    },
    ...
}
```

### Changing Interest Rates

Edit the `"rate_min"` / `"rate_max"` in each band:

```python
"LOW_RISK": {
    ...
    "rate_min": 9.5,   # Reduced from 10.5
    "rate_max": 10.5,  # Reduced from 11.5
    ...
}
```

### Changing Negotiation Rounds

Edit `"max_negotiation_rounds"`:

```python
"MEDIUM_RISK": {
    ...
    "max_negotiation_rounds": 2,  # Increased from 1
    ...
}
```

---

## Testing

### Test High-Approval PAN
```bash
curl -X GET http://localhost:8000/credit-score/ABCDE1234F
```
Expect: `"credit_score": 820, "eligible_for_loan": true`

### Test Medium-Risk PAN
```bash
curl -X GET http://localhost:8000/credit-score/XYZPQ5678K
```
Expect: `"credit_score": 680, "credit_band": "Medium Risk"`

### Test Hard-Reject PAN
```bash
curl -X GET http://localhost:8000/credit-score/QRSTU3456S
```
Expect: `"credit_score": 285, "eligible_for_loan": false`

### Test Full /assess Flow
```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{
    "pan_number": "ABCDE1234F",
    "preferred_language": "en",
    "gender": "Male",
    "married": "Yes",
    "dependents": "1",
    "education": "Graduate",
    "self_employed": "No",
    "applicant_income": 5000,
    "coapplicant_income": 1500,
    "loan_amount": 150,
    "loan_amount_term": 360,
    "credit_history": 1,
    "property_area": "Urban"
  }'
```
Expect: Full response with `credit_score`, `offered_rate`, `max_negotiation_rounds`

---

## Frontend Integration

### Flow in Chatbot

1. **After KYC**: Call `GET /credit-score/{pan}`
   - Show animated credit score reveal card
   - Display band + improvement tips (if rejected)
   - If rejected, END conversation with reapply message

2. **If Eligible**: Call `POST /assess` with `pan_number` + `preferred_language`
   - Store `max_negotiation_rounds` from response
   - Proceed to loan selection

3. **Loan Selection**: Call `POST /negotiate/start` with `max_negotiation_rounds`
   - Negotiation respects band limits
   - Medium Risk can only negotiate 1 round
   - High Risk cannot negotiate (fixed rate)

---

## Production Notes

1. **PAN Validation**: Currently regex-based. In production, integrate with:
   - NSDL API for PAN validation
   - Real CIBIL API for actual credit score
   - KYC registry for ID verification

2. **Score Cache**: Currently in-memory. Consider Redis/DynamoDB for:
   - Caching credit scores (24hr TTL)
   - Session persistence
   - Multi-server deployments

3. **Security**:
   - Mask PANs in logs/responses (✓ already done)
   - Hash PANs in storage
   - Encrypt assessment data at rest
   - Implement rate limiting on /credit-score endpoint

4. **Audit Trail**:
   - Log all /assess calls with timestamp + PAN hash
   - Track score changes over time
   - Monitor outliers (e.g., same PAN, different scores)

---

## FAQ

**Q: Can I use real CIBIL scores?**
A: Yes. Replace `get_credit_score()` to call CIBIL API instead of simulation. Structure stays same.

**Q: What if PAN is invalid?**
A: `simulate_credit_score()` raises `ValueError`. Frontend should catch and show error.

**Q: How do I test with different scores?**
A: Use provided demo PANs, or tweak `simulate_credit_score()` to return fixed values temporarily.

**Q: Can I bypass the 300 minimum?**
A: Yes, but not recommended for demo realism. Edit `CREDIT_SCORE_BANDS` to remove hard reject band.

**Q: What's 60% credit + 40% XGBoost?**
A: Weighting to combine two risk signals. Adjust if needed:
```python
combined = (credit_normalized * 0.70) + (xgboost_prob * 100 * 0.30)  # 70/30 split
```

**Q: How are demo PANs stored?**
A: In `DEMO_PAN_SCORES` dict in `credit_score.py`. Override dynamically via database in production.
