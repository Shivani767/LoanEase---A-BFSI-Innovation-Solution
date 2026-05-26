# Frontend Chatbot Integration Notes

This backend is ready for the existing LoanEase chatbot to call `POST /assess` after KYC completion.
No frontend code has been modified.

## Integration Flow

1. Collect KYC values in chatbot flow.
2. Submit to `POST /assess`.
3. Render:
   - Risk badge color by `risk_tier`:
     - `Low Risk` -> green
     - `Medium Risk` -> yellow
     - `High Risk` -> red
   - Bullet list from `shap_explanation`.
4. Store `application_id` in chat state for later `POST /explain/{application_id}`.

## Example Client Call

```ts
const response = await fetch("http://localhost:8000/assess", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    gender: "Male",
    married: "Yes",
    dependents: "1",
    education: "Graduate",
    self_employed: "No",
    applicant_income: 5000,
    coapplicant_income: 1500,
    loan_amount: 150,
    loan_amount_term: 360,
    credit_history: 1,
    property_area: "Urban"
  })
});

const data = await response.json();
```

## Suggested Chat Message Template

```text
Based on your profile, you're approved! Here's why:
- Strong credit history significantly supports approval
- Income profile improves repayment confidence
- Requested loan amount is aligned with applicant profile
Here are your personalized offers...
```
