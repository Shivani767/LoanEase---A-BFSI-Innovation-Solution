# 🏦 LoanEase — Agentic BFSI Innovation Solution

 
> Agentic AI personal loan system where a Master Agent orchestrates specialized agents across KYC verification, credit underwriting, loan recommendation & negotiation, and sanction-letter issuance with an auditable blockchain trail.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?logo=vite)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)

---

## 🎯 Vision
Traditional loan management systems are cumbersome and archaic. **LoanEase** redefines the experience by combining an intuitive AI-powered interface with enterprise-grade security, making credit accessible and the application process effortless.

---

## ✨ Key Features

### 🤖 AI-Powered Assistant
Experience a seamless, conversational loan journey. Our AI assistant guides you from the first "Hello" to the final sanction letter.
- **Natural Language Interaction**: No complex forms; just chat.
- **Instant Eligibility Assessment**: Real-time credit evaluation.
- **Smart Offer Generation**: Personalized loan terms based on your profile.
- **Multi-Channel Support**: Web chat and WhatsApp share the same loan journey and channel-aware prompts.

### 📊 Decision Dashboard
The post-decision flow now surfaces a richer underwriting summary.
- **Live Credit Insights**: Credit score, risk tier, and SHAP factors are shown with updated banding.
- **Post-Sanction Analytics**: EMI, total payable, total interest, and benchmark comparisons come from the analytics endpoint.
- **Sanction Letter Export**: The sanction letter now has a working PDF download action and an analytics shortcut.

### 🔗 Blockchain Transparency
The blockchain explorer now mirrors the backend block metadata more closely.
- **Block Typing**: Explorer cards distinguish genesis, transaction, and sanction blocks.
- **Stable Explorer Stats**: Chain validity, active sanctions, and PoW difficulty are surfaced consistently.
- **Tamper Demo Fallbacks**: The tamper demo can still run with a fallback reference when a live sanction reference is unavailable.

### 📊 LoanEase vs Traditional Lending
We’ve benchmarked our performance against industry standards to ensure our borrowers get the best experience.

| Feature | Traditional Bank | Loan Agent/DSA | **LoanEase (AI)** |
| :--- | :---: | :---: | :---: |
| **Approval Time** | 7–10 Days | 3–5 Days | **< 5 Minutes** |
| **Availability** | Bank Hours | Work Hours | **24/7 Instant** |
| **Sanction Letter** | Physical/Post | Email/Manual | **Instant Digital** |
| **Audit Trail** | Paper-based | Fragmented | **Blockchain Secured** |
| **Effort** | High Manual | Moderate | **Zero Paperwork** |

---

## 🧠 System Architecture

### End-to-End Flow
```mermaid
flowchart LR
  U[Applicant] -->|Web Chat / WhatsApp UI| FE[Frontend (React + TS)]
  FE -->|REST + multipart uploads| API[Backend API (FastAPI)]

  API --> MA[Master Agent Orchestrator]
  MA --> KYC[KYC Agent\nOCR + PAN/Aadhaar validation]
  MA --> UW[Underwriting Agent\nXGBoost risk score + SHAP]
  MA --> REC[Recommendation Logic\nOffer + tenure + rate]
  MA --> NEG[Negotiation Agent\nCounter-offers + limits]
  MA --> TR[Translation Agent\nEN/HI + Hinglish intent]
  MA --> BC[Blockchain Agent / Service\nSanction letter sealing + verification]

  API --> STORE[(Session + Application Store)]
  UW --> ART[(Model Artifacts)]
  BC --> CHAIN[(Tamper-evident Ledger)]
```

### Agent Responsibilities
- Master Agent: routes tasks, enforces stage transitions, and composes final responses.
- KYC Agent: OCR extraction + cross-document verification and eligibility checks.
- Underwriting Agent: risk scoring (XGBoost) + SHAP explainability narratives.
- Negotiation Agent: policy-driven counter-offers (risk-tier aware), escalation handling.
- Blockchain Agent: sanction-letter generation, signing, hashing, and on-chain reference creation.
- Translation Agent: multilingual support and intent handling for mixed-language inputs.

## 🛠️ Tech Stack

### Frontend & Core
- **React 18 + TypeScript**: Type-safe, component-driven architecture.
- **Vite**: Ultra-fast development and build environment.
- **TanStack Query**: High-performance data fetching and caching.

### UI & UX
- **Tailwind CSS**: Utility-first styling with custom EY design tokens.
- **shadcn/ui**: Accessible, high-quality component primitives.
- **Lucide React**: Vector-based, professional iconography.
- **Recharts**: Interactive data visualizations and comparison charts.

### Utilities
- **Zod**: Robust schema validation for user inputs.
- **Sonner**: Elegant, non-intrusive toast notifications.
- **Date-fns**: Precision date handling for repayment schedules.

---

## 🎨 Design Philosophy 
LoanEase is built to feel like a premium, enterprise-grade financial tool:
- **Palette**: Dark Mode optimized with `Black (#212121)` and `Yellow (#FFE600)`.
- **Typography**: `Inter` and `DM Sans` for maximum readability and a professional feel.
- **Interactions**: Subtle micro-animations (float, slide-up) and glassmorphism effects for a modern UX.

---

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) (v18 or higher)
- [npm](https://www.npmjs.com/) or [yarn](https://yarnpkg.com/)

### Installation

1. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

3. **Open in your browser**  
   Navigate to [http://localhost:8080](http://localhost:8080)

---

## 📁 Project Structure
```text
LoanEase---A-BFSI-Innovation-Solution/
├── frontend/
│   ├── src/
│   │   ├── components/      # Functional and UI components
│   │   │   ├── ui/          # shadcn and Radix primitives
│   │   │   └── ...          # Feature components
│   │   │   ├── ChannelSelector.tsx
│   │   │   ├── WhatsAppChat.tsx
│   │   │   └── WhatsAppInput.tsx
│   │   ├── pages/           # App-level page views
│   │   │   └── WhatsAppPage.tsx
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # Shared frontend utilities
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── agents/              # Master + specialized agents
│   ├── app/                 # Unified FastAPI app (chat, KYC, underwriting, pipeline)
│   ├── services/            # OCR, SHAP, PDF generator, memory/context helpers
│   ├── artifacts/           # Model + metadata (and sample sanctions)
│   ├── data/                # Datasets and stored applications
│   ├── requirements.txt
│   └── train_model.py
├── README.md
└── LICENSE
```

---

## 📈 Impact & Innovation
- **75% Faster Decisions**: Drastic reduction in turnaround time vs traditional banks.
- **50% Effort Reduction**: Automated agent-driven workflows minimize manual data entry.
- **100% Digital Journey**: From KYC to signed sanction letters, no physical touchpoints required.

---

## 🚧 Roadmap
- [ ] Multi-regional Support & Language Localization
- [ ] Integration with major Core Banking Systems (CBS)
- [ ] Advanced Fraud Detection using ML models
- [ ] Mobile App (Progressive Web App support)

---

## 📚 API Reference

The tables below reflect the currently mounted routes in the unified backend and the standalone service modules. Every service also exposes OpenAPI docs at `/docs` on its local port.

### Unified Backend (`backend/app/main.py`)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/` | Service banner / root health entry |
| `GET` | `/health` | Unified backend health |
| `POST` | `/session/save` | Persist chat/session state |
| `GET` | `/session/{session_id}` | Load stored session data |
| `POST` | `/escalation/preferences` | Save escalation callback preferences |
| `GET` | `/analytics/{session_id}` | EMI, payoff, risk, and benchmark analytics |
| `POST` | `/pipeline/start` | Start the orchestrated pipeline |
| `GET` | `/pipeline/log/{session_id}` | Fetch pipeline step log |
| `GET` | `/credit-score/{pan_number}` | Credit score simulation and banding |
| `GET` | `/credit/credit-score` | Legacy credit-score alias |
| `POST` | `/assess` | Risk assessment and decision generation |
| `POST` | `/credit/assess` | Legacy assessment alias |
| `POST` | `/explain/{application_id}` | Stored-application explanation and SHAP waterfall |
| `POST` | `/escalation/callback-preference` | Legacy callback preference alias |
| `POST` | `/kyc/extract/pan` | PAN OCR extraction and validation |
| `POST` | `/kyc/extract/aadhaar` | Aadhaar OCR extraction and validation |
| `POST` | `/kyc/verify` | Cross-document KYC verification |
| `POST` | `/negotiate/start` | Start a negotiation session |
| `POST` | `/negotiate/start-from-underwriting` | Start negotiation from underwriting context |
| `POST` | `/negotiate/counter` | Submit a counter-offer |
| `POST` | `/negotiate/accept` | Accept the current offer |
| `POST` | `/negotiate/escalate` | Escalate to a human officer |
| `GET` | `/negotiate/history/{session_id}` | Negotiation history and current state |
| `POST` | `/translate` | Translate between English and Hindi |
| `POST` | `/detect-hinglish-intent` | Detect Hinglish intent |
| `POST` | `/chat` | Channel-aware chat endpoint |
| `POST` | `/chat/stream` | Streaming chat endpoint |
| `POST` | `/intent/classify` | Classify the current user intent |
| `POST` | `/explain/credit` | Credit explanation helper |
| `POST` | `/explain/negotiation` | Negotiation explanation helper |
| `POST` | `/generate/rejection` | Generate rejection messaging |
| `GET` | `/groq/health` | Groq integration health |

### Blockchain Service (`backend/blockchain_service.py` and blockchain agent)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/blockchain/sanction` | Register and seal a sanction record |
| `GET` | `/blockchain/verify/{reference}` | Verify a blockchain reference |
| `GET` | `/blockchain/chain` | Return the blockchain chain payload |
| `GET` | `/blockchain/stats` | Return chain statistics |
| `GET` | `/blockchain/explorer-data` | Explorer-ready chain metadata |
| `POST` | `/blockchain/tamper-test` | Run tamper simulation |
| `GET` | `/blockchain/verify-chain` | Chain verification summary |
| `GET` | `/health` | Blockchain service health |

### Negotiation (Embedded)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/negotiate/start` | Start a negotiation session from risk context |
| `POST` | `/negotiate/start-from-underwriting` | Start negotiation via underwriting output |
| `POST` | `/negotiate/counter` | Submit a counter request |
| `POST` | `/negotiate/accept` | Accept current negotiated offer |
| `POST` | `/negotiate/escalate` | Escalate case to a human officer |
| `GET` | `/negotiate/history/{session_id}` | Retrieve session history |
| `GET` | `/health` | Negotiation service health |
| `GET` | `/negotiate/analytics` | Negotiation analytics summary |

### Translation (Embedded)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/translate` | Translate text between English and Hindi |
| `POST` | `/detect-hinglish-intent` | Detect intent from Hinglish input |
| `GET` | `/health` | Translation service health |

### KYC Verification (Embedded)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/kyc/extract/pan` | Extract PAN fields and validate |
| `POST` | `/kyc/extract/aadhaar` | Extract Aadhaar fields and validate |
| `POST` | `/kyc/verify` | Cross-validate PAN and Aadhaar |
| `POST` | `/kyc/extract/auto` | Auto-detect document type and extract |
| `GET` | `/health` | KYC service health |

## ⚙️ Backend Services

LoanEase uses a unified FastAPI backend with agent-based modules:

- `backend/app/` for chat, underwriting, KYC OCR flows, session storage, and pipeline routes.
- `backend/agents/` for Master Agent orchestration and specialized agent logic (KYC, underwriting, negotiation, translation, blockchain).
- `backend/blockchain_service.py` + `backend/agents/blockchain_agent/` for sanction-letter sealing and blockchain verification endpoints.

### Credit Underwriting Backend (`backend/`)

#### What it does
- Trains an XGBoost classifier using `backend/data/loan_train.csv`.
- Produces prediction artifacts in `backend/artifacts/`.
- Exposes underwriting APIs for assessment, explanation, and health monitoring.
- Returns SHAP-based plain-English factor explanations.
- Serves a post-decision analytics endpoint at `/analytics/{session_id}` for EMI, payoff, and benchmark summaries.

#### Setup
From repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Dataset
Place Kaggle Loan Prediction dataset CSV at:

- `backend/data/loan_train.csv`

Expected columns:

- `Gender`, `Married`, `Dependents`, `Education`, `Self_Employed`
- `ApplicantIncome`, `CoapplicantIncome`, `LoanAmount`, `Loan_Amount_Term`
- `Credit_History`, `Property_Area`, `Loan_Status`

#### Train model

```powershell
python train_model.py --data data/loan_train.csv --artifacts artifacts
```

Training pipeline includes:

- Missing-value imputation: median (numeric), mode (categorical)
- Label encoding for categoricals
- 80/20 train-test split
- GridSearchCV tuning for `max_depth`, `n_estimators`, `learning_rate`
- Classification report and confusion matrix in console output

Artifacts generated:

- `backend/artifacts/loan_model.pkl`
- `backend/artifacts/preprocessor.pkl`
- `backend/artifacts/metadata.json`

#### Run API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docs: `http://localhost:8000/docs`

#### API endpoints (validated)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health, model version, accuracy, uptime |
| `GET` | `/credit-score/{pan_number}` | Credit score simulation, score band, and eligibility context |
| `POST` | `/assess` | Risk assessment and decision generation |
| `POST` | `/explain/{application_id}` | Full explanation and SHAP waterfall for a stored application |

#### Risk bands
- `300-549` = High Risk
- `550-699` = Medium Risk
- `700-900` = Low Risk

#### Risk policy (current)
- Final risk combines credit score band + model risk score.
- All users remain loan-eligible; risk tier changes pricing and negotiation limits.
- Typical interest-rate guidance: `Low Risk` 9-11%, `Medium Risk` 11-13%, `High Risk` 13-15%.

### Dynamic Negotiation (Embedded)

#### What it does
- Runs stateful in-memory negotiation sessions.
- Applies risk-aware pricing policy with configurable limits.
- Returns plain-English reasoning for each response.
- Computes EMI, total payable, and savings with reducing-balance formula.
- Performs basic intent detection from applicant messages.
- Enforces 48-hour session expiry.

#### Business constants
- `RATE_CEILING = 14.0`
- `RATE_FLOOR = 10.5`
- `MAX_ROUNDS = 3`
- `CONCESSION_STEP = 0.25`

#### Underwriting integration
Typical flow:

1. Call underwriting `POST /assess`.
2. Use returned `risk_score` and `risk_tier`.
3. Start negotiation via `POST /negotiate/start`.

Optional adapter endpoint:

- `POST /negotiate/start-from-underwriting`

#### EMI formula

- `EMI = P * R * (1+R)^N / ((1+R)^N - 1)`
- `P`: principal
- `R`: monthly interest rate (`annual_rate / 12 / 100`)
- `N`: tenure in months

#### CORS
Allowed origins include:

- `http://localhost:8080`
- `http://127.0.0.1:8080`
- `http://localhost:3000`
- `FRONTEND_DOMAIN` env var (default `https://loanease.example.com`)

#### Core endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/negotiate/start` | Start a negotiation session from supplied risk context |
| `POST` | `/negotiate/start-from-underwriting` | Start negotiation by first calling underwriting `/assess` |
| `POST` | `/negotiate/counter` | Submit user counter-request and get a revised offer |
| `POST` | `/negotiate/accept` | Accept current negotiated offer and close session |
| `POST` | `/negotiate/escalate` | Escalate case to a human loan officer |
| `GET` | `/negotiate/history/{session_id}` | Retrieve current session state and conversation history |
| `GET` | `/health` | Service health, uptime, and active session count |

### Translation (Embedded) — Multilingual Support

#### What it does
- Translates text between English and Hindi using Google Translate free tier.
- Detects Hinglish input (Hindi written in English letters) and maps to intents.
- Provides language detection, fallback handling, and caching.
- Enables chatbot to communicate in user's preferred language.

#### API endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/translate` | Translate text between English and Hindi |
| `POST` | `/detect-hinglish-intent` | Detect intent from Hinglish (Hindi in English letters) |
| `GET` | `/health` | Service health and uptime |

#### Supported Hinglish Intents

- `LOAN_REQUEST` - "loan chahiye", "mujhe loan", "loan lena hai"
- `RATE_QUERY` - "kitna rate", "rate kya hai", "interest kya"
- `COUNTER_REQUEST` - "aur kam karo", "aur neeche", "kamtar karo" (negotiation)
- `ACCEPTANCE` - "theek hai", "manzoor", "accept"
- `CANCELLATION` - "cancel", "nahi chahiye", "band karo"
- `KYC_PROMPT` - "documents", "kyc", "pan card", "aadhar"

#### Frontend Features

- **Language Switcher**: EN/HI pills in chat header (yellow active state)
- **Auto-detection**: Detects user language from typed message via franc-min CDN
- **Hardcoded Critical Strings**: Core messages (approval, rejection, KYC) in both languages
- **Number Formatting**: Indian style (₹5,00,000) in Hindi mode
- **Translation Caching**: 24-hour client-side cache for translations
- **Channel Selector**: Users can choose web chat or WhatsApp entry from the hero flow.
- **Channel-Aware Prompts**: Backend prompts adjust response length and formatting per channel.

#### Example Usage

**Translate endpoint:**

```bash
curl -X POST "http://localhost:8000/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Congratulations! Your loan is approved.",
    "source_language": "en",
    "target_language": "hi"
  }'
```

**Hinglish intent detection:**

```bash
curl -X POST "http://localhost:8000/detect-hinglish-intent" \
  -H "Content-Type: application/json" \
  -d '{"message": "aur kam karo rate"}'
```

#### How to Add a New Language

1. **Add UI strings**: update `frontend/src/lib/translations.ts`
2. **Update agent logic**: extend language/intent handling under `backend/agents/translation_agent/`

### Frontend Decision Flow

- **Agent Activity Panel**: Collapsible floating sidebar that expands only when it is visible or opened manually.
- **Credit Score Card**: Score 592 is treated as Medium Risk in the UI thresholding.
- **Sanction Letter**: Download PDF now triggers a real export flow.
- **Analytics Dashboard**: Pulls live session analytics from `/analytics/{session_id}` and renders charts from backend data.

### KYC Verification (Embedded) — OCR + Document Validation

#### What it does
- Extracts PAN fields from uploaded JPG/PNG/PDF.
- Extracts Aadhaar fields from uploaded JPG/PNG/PDF.
- Runs cross-document validation (name + DOB + age eligibility).
- Returns structured KYC status and reference ID for downstream flow.

#### API endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/kyc/extract/pan` | Extract PAN fields + validation |
| `POST` | `/kyc/extract/aadhaar` | Extract Aadhaar fields + validation |
| `POST` | `/kyc/verify` | Cross-validate PAN and Aadhaar together |
| `POST` | `/kyc/extract/auto` | Auto-detect doc type and extract |
| `GET` | `/health` | Service health, OCR engine status, uptime |

---

## 🌍 Running Locally

### Frontend (Port 5173)
```powershell
cd frontend
npm install
npm run dev
```

### Backend API (Port 8000)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Blockchain Audit Service (Port 8005, Optional)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn blockchain_service:app --reload --host 0.0.0.0 --port 8005
```

---
© 2026 LoanEase — A BFSI Innovation Solution.
