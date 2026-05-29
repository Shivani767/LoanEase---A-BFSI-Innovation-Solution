/**
 * Language detection using franc-min library (via CDN).
 * franc-min provides lightweight language detection without dependencies.
 */

export interface DetectionResult {
  detected: boolean;
  language: "en" | "hi" | "unknown";
  confidence: number;
}

/**
 * Detect language from text using franc-min.
 * Falls back to English if detection fails or isn't available.
 */
export const detectLanguage = async (
  text: string
): Promise<DetectionResult> => {
  if (!text || text.trim().length < 3) {
    return {
      detected: false,
      language: "unknown",
      confidence: 0,
    };
  }

  try {
    // Check if franc is available globally (loaded via CDN)
    // @ts-expect-error - franc-min loaded via CDN
    if (typeof franc !== "undefined") {
      // @ts-expect-error - franc global from CDN
      const result = franc(text);

      // franc returns language code, e.g., "eng", "hin"
      if (result === "eng" || result === "en") {
        return { detected: true, language: "en", confidence: 0.9 };
      }
      if (result === "hin" || result === "hi") {
        return { detected: true, language: "hi", confidence: 0.9 };
      }
    }

    // Fallback: simple heuristic detection
    // Check for Hindi Unicode ranges
    const hindiRegex = /[\u0900-\u097F]/g;
    const hindiMatches = text.match(hindiRegex);

    if (hindiMatches && hindiMatches.length / text.length > 0.3) {
      return { detected: true, language: "hi", confidence: 0.7 };
    }

    // Default to English
    return {
      detected: true,
      language: "en",
      confidence: 0.5,
    };
  } catch (error) {
    console.error("Language detection error:", error);
    return {
      detected: false,
      language: "unknown",
      confidence: 0,
    };
  }
};

/**
 * Format Indian rupees with correct Indian number formatting
 */
export const formatIndianRupees = (amount: number | null | undefined): string => {
  // Handle null/undefined
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0'
  }
  
  amount = Math.round(Number(amount))
  
  // Indian format: 
  // last 3 digits, then groups of 2
  const str = amount.toString()
  
  if (str.length <= 3) {
    return '₹' + str
  }
  
  // Split into last 3 and rest
  const last3 = str.slice(-3)
  const rest = str.slice(0, -3)
  
  // Group rest in pairs from right
  const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')
  
  return '₹' + grouped + ',' + last3
}

/**
 * Format number in Indian style (e.g., 5,00,000 instead of 500,000)
 * @deprecated Use formatIndianRupees instead
 */
export const formatIndianNumber = (num: number): string => {
  const parts = num.toString().split(".");
  const integerPart = parts[0].replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return parts.length > 1 ? `${integerPart}.${parts[1]}` : integerPart;
};

/**
 * Format currency in Indian style with rupee symbol
 * @deprecated Use formatIndianRupees instead
 */
export const formatIndianCurrency = (amount: number): string => {
  return `₹${formatIndianNumber(Math.floor(amount))}`;
};

/**
 * Format EMI with proper currency styling
 */
export const formatEMI = (amount: number, language: "en" | "hi"): string => {
  const currency = formatIndianRupees(amount);
  const perMonth = language === "en" ? "per month" : "प्रति माह";
  return `${currency} ${perMonth}`;
};

/**
 * Map Hindi risk tier labels
 */
export const getRiskTierLabel = (
  tier: string,
  language: "en" | "hi"
): string => {
  const tierLower = tier.toLowerCase();

  if (tierLower.includes("low")) {
    return language === "en" ? "Low Risk" : "कम जोखिम";
  }
  if (tierLower.includes("medium")) {
    return language === "en" ? "Medium Risk" : "मध्यम जोखिम";
  }
  if (tierLower.includes("high")) {
    return language === "en" ? "High Risk" : "उच्च जोखिम";
  }

  return tier;
};
