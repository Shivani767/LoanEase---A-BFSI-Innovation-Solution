/**
 * Hardcoded translations for critical LoanEase messages.
 * English & Hindi, no API dependency for these core strings.
 */

export const TRANSLATIONS = {
  // Language names
  language: {
    en: "English",
    hi: "हिंदी",
  },

  // Opening messages
  opening: {
    en: "Hello! I'll help you find the perfect loan. What amount are you looking for?",
    hi: "नमस्ते! मैं आपको सही लोन खोजने में मदद करूँगा। आप कितनी राशि की तलाश में हैं?",
  },

  // KYC verification prompts
  kyc_intro: {
    en: "For KYC verification, please share your PAN number.",
    hi: "केवाईसी सत्यापन के लिए, कृपया अपनी पैन संख्या साझा करें।",
  },

  kyc_upload: {
    en: "Please upload your PAN card and Aadhaar card to verify your identity.",
    hi: "अपनी पहचान सत्यापित करने के लिए कृपया अपना पैन कार्ड और आधार कार्ड अपलोड करें।",
  },

  kyc_processing: {
    en: "Your details are captured. I will now verify your profile and fetch your credit score. Please wait while we process the bureau check.",
    hi: "आपका विवरण दर्ज किया गया है। अब मैं आपकी प्रोफ़ाइल सत्यापित करूंगा और आपका क्रेडिट स्कोर प्राप्त करूंगा। कृपया प्रतीक्षा करें जबकि हम ब्यूरो की जांच को संसाधित करते हैं।",
  },

  // Credit score result
  credit_score_text: {
    en: "Credit Score",
    hi: "क्रेडिट स्कोर",
  },

  // Approval messages
  approved: {
    en: "Congratulations! Based on your profile, your loan is approved.",
    hi: "बधाई हो! आपकी प्रोफ़ाइल के आधार पर, आपका लोन स्वीकृत हो गया है।",
  },

  approved_with_conditions: {
    en: "Your loan has been approved with conditions. Please review the offer details.",
    hi: "आपका लोन शर्तों के साथ स्वीकृत हो गया है। कृपया प्रस्ताव विवरण की समीक्षा करें।",
  },

  // Rejection message
  rejected: {
    en: "We're sorry. Your current credit profile does not meet our eligibility criteria.",
    hi: "हमें खेद है। आपकी वर्तमान क्रेडिट प्रोफ़ाइल हमारी पात्रता मानदंड को पूरा नहीं करती।",
  },

  // Offer card labels
  loan_offer: {
    en: "Loan Offer",
    hi: "लोन प्रस्ताव",
  },

  rate: {
    en: "Rate",
    hi: "दर",
  },

  tenure: {
    en: "Tenure",
    hi: "अवधि",
  },

  emi: {
    en: "EMI",
    hi: "ईएमआई",
  },

  total_payable: {
    en: "Total Payable",
    hi: "कुल देय",
  },

  accept: {
    en: "Accept",
    hi: "स्वीकार करें",
  },

  negotiate: {
    en: "Negotiate",
    hi: "बातचीत करें",
  },

  // Risk tier labels
  low_risk: {
    en: "Low Risk",
    hi: "कम जोखिम",
  },

  medium_risk: {
    en: "Medium Risk",
    hi: "मध्यम जोखिम",
  },

  high_risk: {
    en: "High Risk",
    hi: "उच्च जोखिम",
  },

  // Negotiation messages
  negotiation_start: {
    en: "Let's negotiate your rate. What rate would you like to request?",
    hi: "आइए अपनी दर पर बातचीत करें। आप किस दर का अनुरोध करना चाहेंगे?",
  },

  negotiation_offer: {
    en: "We can reduce the rate by 0.25% as a goodwill adjustment.",
    hi: "हम सद्भावना समायोजन के रूप में दर को 0.25% कम कर सकते हैं।",
  },

  negotiation_final: {
    en: "This is our best offer based on your risk profile. Will you accept?",
    hi: "यह आपके जोखिम प्रोफ़ाइल के आधार पर हमारा सर्वोत्तम प्रस्ताव है। क्या आप स्वीकार करेंगे?",
  },

  accepted: {
    en: "Congratulations! Your loan has been accepted.",
    hi: "बधाई हो! आपका लोन स्वीकृत हो गया है।",
  },

  // Time units
  per_month: {
    en: "per month",
    hi: "प्रति माह",
  },

  per_annum: {
    en: "per annum",
    hi: "प्रति वर्ष",
  },

  months: {
    en: "months",
    hi: "महीने",
  },

  years: {
    en: "years",
    hi: "साल",
  },

  minutes: {
    en: "minutes",
    hi: "मिनट",
  },

  // UI labels
  input_placeholder_en: "Type your message...",
  input_placeholder_hi: "अपना संदेश लिखें...",

  send_button: {
    en: "Send",
    hi: "भेजें",
  },

  // Toast messages
  language_switched_en: "Switched to English",
  language_switched_hi: "हिंदी में स्विच किया गया",

  language_detected_en: "English detected",
  language_detected_hi: "हिंदी की पहचान की गई",
};

export type TranslationKey = keyof typeof TRANSLATIONS;

export const getTranslation = (
  key: TranslationKey,
  language: "en" | "hi"
): string => {
  const value = TRANSLATIONS[key];

  if (typeof value === "object" && value !== null) {
    return value[language] || (value.en as string);
  }

  // For direct string keys with _en or _hi suffix
  if (language === "en" && key.endsWith("_en")) {
    return value as string;
  }
  if (language === "hi" && key.endsWith("_hi")) {
    return value as string;
  }

  return value as string;
};
