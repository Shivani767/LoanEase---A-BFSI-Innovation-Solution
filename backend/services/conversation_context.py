from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple


AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lakhs|lac|lacs|crore|cr|k|thousand)?", re.IGNORECASE)
PURPOSE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("home_renovation", ("home renovation", "renovation", "repair the house", "paint the house", "home improve")),
    ("medical", ("medical", "hospital", "treatment", "surgery", "emergency", "health")),
    ("wedding", ("wedding", "marriage", "shaadi", "shadi", "function")),
    ("education", ("education", "college", "fees", "study", "course", "tuition")),
    ("business", ("business", "shop", "expand", "inventory", "startup", "working capital", "working-capital")),
    ("debt_consolidation", ("consolidate", "debt", "credit card", "repay loans")),
    ("travel", ("travel", "trip", "vacation", "holiday")),
]

PURPOSE_PROFILES = {
    "medical": {
        "urgency": "high",
        "tone": "empathetic",
        "processing": "priority",
        "opening_message": "Medical emergencies need fast action. I'll prioritize your application.",
        "rate_note": "Medical loans often qualify for our fastest processing track — under 3 minutes.",
        "skip_small_talk": True,
    },
    "home_renovation": {
        "urgency": "medium",
        "tone": "professional",
        "alternative_suggestion": "Have you considered a Home Improvement Loan? Rates can be 0.5-1% lower than personal loans for renovation purposes.",
    },
    "wedding": {
        "urgency": "medium",
        "tone": "warm",
        "tenure_suggestion": "For wedding loans, many borrowers prefer 24-36 months so EMI clears before the next major expense.",
    },
    "education": {
        "urgency": "medium",
        "rate_note": "Education loans may qualify for lower rates. Do you have an admission letter from the institution?",
    },
    "business": {
        "urgency": "medium",
        "redirect_note": "For business purposes, a Business Loan product may offer better terms. However, I can process a personal loan if you prefer.",
    },
    "debt_consolidation": {
        "urgency": "low",
        "special_check": True,
        "note": "For debt consolidation, I need to verify your existing EMI obligations to ensure the new loan doesn't overburden you.",
    },
}

LANGUAGE_HINTS = {
    "hi": (" hindi ", "हिंदी", "namaste", "kripya", "kya", "mujhe", "loan chahiye", "chahiye"),
    "hinglish": ("mujhe", "chahiye", "kaise", "kitna", "please", "bhai", "yaar", "loan", "emi"),
}
HESITATION_PATTERNS = (
    "not sure",
    "maybe",
    "kuch",
    "samajh nahi",
    "don't know",
    "doubt",
    "confused",
    "soch raha",
    "soch rahi",
    "let me think",
    "kya karun",
)
NEGOTIATION_TONE_PATTERNS = {
    "aggressive": ("now", "urgent", "best rate", "final", "immediately", "need lower", "lowest", "deadline"),
    "passive": ("whenever", "whenever possible", "if possible", "maybe", "just checking", "whenever convenient"),
    "moderate": tuple(),
}
INTENT_KEYWORDS = {
    "apply": ("apply", "start", "loan chahiye", "loan चाहिए", "loan lena", "new loan"),
    "eligibility": ("eligible", "eligibility", "qualification", "kitna loan", "how much can i get"),
    "rate": ("interest", "rate", "emi", "interest rate", "apr"),
    "kyc": ("kyc", "pan", "aadhaar", "aadhar", "otp", "upload", "document"),
    "negotiation": ("negotiate", "counter", "reduce rate", "bargain", "lower rate"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_applicant_name(message: str, existing_name: str | None = None) -> str | None:
    if existing_name:
        return existing_name

    text = _normalize(message)
    patterns = [
        r"\bmy name is ([a-z][a-z\s]{1,40})\b",
        r"\bi am ([a-z][a-z\s]{1,40})\b",
        r"\bi'm ([a-z][a-z\s]{1,40})\b",
        r"\bmera naam ([a-z][a-z\s]{1,40})\b",
        r"\bmai(n)? ([a-z][a-z\s]{1,40})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(r"\b(apply|want|need|for|to|loan|please|help)\b.*$", "", candidate).strip()
            if len(candidate.split()) <= 4 and candidate:
                return candidate.title()
    return None


def extract_loan_amount(message: str) -> float | None:
    text = _normalize(message)
    if not text:
        return None

    amount_match = AMOUNT_RE.search(text)
    if not amount_match:
        return None

    value = amount_match.group(1).replace(",", "")
    suffix = (amount_match.group(2) or "").lower()
    try:
        amount = float(value)
    except ValueError:
        return None

    if suffix in {"lakh", "lakhs", "lac", "lacs"}:
        amount *= 100000
    elif suffix in {"crore", "cr"}:
        amount *= 10000000
    elif suffix in {"k", "thousand"}:
        amount *= 1000

    return round(amount, 2)


def extract_loan_purpose(message: str) -> str | None:
    text = _normalize(message)
    for purpose, patterns in PURPOSE_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return purpose
    return None


def infer_language(message: str, existing_language: str | None = None) -> str:
    if existing_language in {"en", "hi", "hinglish"}:
        return existing_language

    text = _normalize(message)
    if any(ch >= "\u0900" and ch <= "\u097f" for ch in message):
        return "hi"

    hi_hits = sum(1 for token in LANGUAGE_HINTS["hi"] if token in text)
    hinglish_hits = sum(1 for token in LANGUAGE_HINTS["hinglish"] if token in text)
    if hi_hits >= 2:
        return "hi"
    if hinglish_hits >= 2:
        return "hinglish"
    return "en"


def detect_hesitation(message: str) -> bool:
    text = _normalize(message)
    return any(pattern in text for pattern in HESITATION_PATTERNS)


def infer_negotiation_tone(message: str, existing_tone: str | None = None) -> str:
    if existing_tone in {"aggressive", "moderate", "passive"}:
        return existing_tone

    text = _normalize(message)
    if any(pattern in text for pattern in NEGOTIATION_TONE_PATTERNS["aggressive"]):
        return "aggressive"
    if any(pattern in text for pattern in NEGOTIATION_TONE_PATTERNS["passive"]):
        return "passive"
    return "moderate"


def extract_questions(message: str) -> list[str]:
    text = (message or "").strip()
    if not text:
        return []
    questions = [segment.strip(" ?।.") for segment in re.split(r"\?+", text) if segment.strip()]
    if message.strip().endswith("?"):
        return questions[-3:]
    return [text] if "?" in text else []


def infer_intent(message: str) -> tuple[str, float]:
    text = _normalize(message)
    if not text:
        return "UNKNOWN", 0.0

    scores: list[tuple[str, float]] = []
    for intent, patterns in INTENT_KEYWORDS.items():
        hit_count = sum(1 for pattern in patterns if pattern in text)
        if hit_count:
            scores.append((intent, min(0.95, 0.35 + hit_count * 0.2)))

    if not scores:
        if len(text.split()) <= 3:
            return "UNKNOWN", 0.35
        return "UNKNOWN", 0.5

    scores.sort(key=lambda item: item[1], reverse=True)
    return scores[0]


def build_context_updates(message: str, current_context: Dict[str, Any] | None = None, stage: str | None = None) -> Dict[str, Any]:
    current_context = current_context or {}
    previous_questions = list(current_context.get("questions_asked", []))
    new_questions = extract_questions(message)
    questions_asked = previous_questions + [q for q in new_questions if q and q not in previous_questions]

    existing_amount = current_context.get("loan_amount")
    amount = extract_loan_amount(message) or existing_amount
    purpose = extract_loan_purpose(message) or current_context.get("loan_purpose")
    language = infer_language(message, current_context.get("language"))
    hesitation_count = int(current_context.get("hesitation_count") or 0)
    if detect_hesitation(message):
        hesitation_count += 1
    tone = infer_negotiation_tone(message, current_context.get("negotiation_tone"))
    intent, confidence = infer_intent(message)

    updates: Dict[str, Any] = {
        "stage": stage or current_context.get("stage") or "kyc",
        "language": language,
        "previous_intent": current_context.get("intent") or current_context.get("previous_intent") or intent,
        "intent": intent,
        "intent_confidence": confidence,
        "hesitation_count": hesitation_count,
        "negotiation_tone": tone,
        "questions_asked": questions_asked,
        "last_user_message": message,
        "last_activity_at": now_iso(),
    }

    if amount is not None:
        updates["loan_amount"] = amount
    if purpose:
        updates["loan_purpose"] = purpose

    name = extract_applicant_name(message, current_context.get("applicant_name"))
    if name:
        updates["applicant_name"] = name

    return updates


def build_memory_prompt_block(context: Dict[str, Any]) -> str:
    applicant = context.get("applicant_name") or "Applicant"
    purpose = context.get("loan_purpose") or "unknown"
    tone = context.get("negotiation_tone") or "moderate"
    stage = context.get("stage") or "kyc"
    previous_intent = context.get("previous_intent") or "UNKNOWN"
    questions = context.get("questions_asked") or []
    recent_questions = ", ".join(str(question) for question in questions[-3:]) or "none"
    amount = context.get("loan_amount")
    language = context.get("language") or "en"

    purpose_guidance = ""
    if purpose in PURPOSE_PROFILES:
        profile = PURPOSE_PROFILES[purpose]
        urgency = profile.get("urgency", "medium")
        guidance = [f"Urgency: {urgency}", f"Tone: {profile.get('tone', tone)}"]
        if "opening_message" in profile:
            guidance.append(f"Opening Note: {profile['opening_message']}")
        if "rate_note" in profile:
            guidance.append(f"Rate Note: {profile['rate_note']}")
        if "alternative_suggestion" in profile:
            guidance.append(f"Alternative Suggestion: {profile['alternative_suggestion']}")
        if "tenure_suggestion" in profile:
            guidance.append(f"Tenure Suggestion: {profile['tenure_suggestion']}")
        if "redirect_note" in profile:
            guidance.append(f"Redirect Note: {profile['redirect_note']}")
        if "note" in profile:
            guidance.append(f"Important Note: {profile['note']}")
        purpose_guidance = " | ".join(guidance)

    lines = [
        "Conversation memory:",
        f"Applicant: {applicant}",
        f"Purpose: {purpose}",
        f"Purpose guidance: {purpose_guidance or 'none'}",
        f"Loan amount: {amount if amount is not None else 'unknown'}",
        f"Tone: {tone}",
        f"Stage: {stage}",
        f"Previous intent: {previous_intent}",
        f"Language: {language}",
        f"Previously asked about: {recent_questions}",
    ]
    return "\n".join(lines)


def low_confidence_clarification(context: Dict[str, Any], intent: str | None = None, confidence: float | None = None) -> Dict[str, Any]:
    intent = (intent or context.get("intent") or "UNKNOWN").upper()
    language = context.get("language") or "en"
    applicant = context.get("applicant_name") or "there"
    amount = context.get("loan_amount")
    amount_text = f" for around {amount:,.0f}" if isinstance(amount, (int, float)) else ""

    if intent in {"KYC", "UNKNOWN"} and (context.get("stage") or "kyc") == "kyc":
        message = (
            "I want to make sure I help you correctly - are you looking to apply for a loan, check your eligibility, or upload documents?"
            if language == "en"
            else "Main yeh pakka karna chahta hoon ki main sahi madad karun - kya aap loan apply karna chahte hain, eligibility check karna chahte hain, ya documents upload karna hai?"
        )
        quick_replies = [
            {"label": "Apply for loan", "value": "I want to apply for a loan"},
            {"label": "Check eligibility", "value": "Check my eligibility"},
            {"label": "Upload documents", "value": "I want to upload my KYC documents"},
        ]
    else:
        message = (
            f"I want to help you properly, {applicant}. Could you tell me whether you want to apply, negotiate, or ask about your offer{amount_text}?"
            if language == "en"
            else f"Main aapki madad sahi tarike se karna chahta hoon, {applicant}. Kya aap apply karna chahte hain, negotiate karna chahte hain, ya apne offer ke baare mein poochna chahte hain{amount_text}?"
        )
        quick_replies = [
            {"label": "Apply", "value": "I want to apply for a loan"},
            {"label": "Eligibility", "value": "Check my eligibility"},
            {"label": "Talk to agent", "value": "I want to speak with a loan officer"},
        ]

    return {
        "message": message,
        "quick_replies": quick_replies,
        "intent": intent,
        "intent_confidence": confidence if confidence is not None else context.get("intent_confidence", 0.0),
        "needs_clarification": True,
    }


def build_error_recovery(error_text: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    text = _normalize(error_text)
    context = context or {}

    if any(keyword in text for keyword in ("ocr", "scan", "document", "image", "aadhaar", "pan")):
        return {
            "message": "The document scan had some trouble reading that file. Try a brighter, flat photo with all four corners visible. Shall I try again?",
            "quick_replies": [
                {"label": "Try again", "value": "Please try the scan again"},
                {"label": "Upload clearer photo", "value": "I will upload a clearer photo"},
            ],
            "recovery_type": "ocr_failure",
        }

    if any(keyword in text for keyword in ("timeout", "timed out", "credit", "underwriting", "assessment")):
        return {
            "message": "Our credit system is taking a moment. I'll retry automatically - this sometimes happens during peak hours.",
            "quick_replies": [
                {"label": "Retry now", "value": "Please retry the credit check"},
                {"label": "Wait", "value": "I'll wait a moment"},
            ],
            "recovery_type": "credit_timeout",
        }

    if any(keyword in text for keyword in ("otp", "mobile", "deliver", "sms", "verification")):
        return {
            "message": "The OTP may take up to 2 minutes. Check your registered mobile. Want me to resend to the same number?",
            "quick_replies": [
                {"label": "Resend OTP", "value": "Please resend the OTP"},
                {"label": "Check number", "value": "Which mobile number is registered?"},
            ],
            "recovery_type": "otp_not_delivered",
        }

    return {
        "message": "Something interrupted the flow, but I can help you continue. Would you like me to try again or switch to a simpler step?",
        "quick_replies": [
            {"label": "Try again", "value": "Please try again"},
            {"label": "Simplify", "value": "Explain it in simple steps"},
        ],
        "recovery_type": "general_error",
    }


def build_nudge(stage: str, context: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    context = context or {}
    last_activity_at = context.get("last_activity_at")
    if not last_activity_at:
        return None

    try:
        last_activity = datetime.fromisoformat(str(last_activity_at).replace("Z", "+00:00"))
    except ValueError:
        return None

    idle_seconds = (datetime.now(timezone.utc) - last_activity).total_seconds()
    if idle_seconds < 90:
        return None

    normalized_stage = (stage or context.get("stage") or "kyc").lower()
    if normalized_stage == "kyc":
        message = "Still there? I'm ready whenever you want to upload your documents."
    elif normalized_stage == "credit":
        message = "Take your time reviewing. I can explain any part of the offer."
    elif normalized_stage in {"reject", "rejected", "decline"}:
        message = "I can tell you exactly what would improve your profile for next time."
    elif normalized_stage in {"negotiation", "offer"}:
        message = "No rush - if you want, I can walk you through the offer or the EMI options again."
    else:
        message = "I'm here whenever you're ready to continue."

    return {
        "message": message,
        "stage": normalized_stage,
        "should_nudge": True,
        "idle_seconds": int(idle_seconds),
    }
