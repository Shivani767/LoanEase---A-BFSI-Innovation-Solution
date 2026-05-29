/**
 * Utility to fetch translations from the translation backend.
 * Supports caching to minimize API calls.
 */
import { API_BASE_URL } from "@/config";

interface TranslationCache {
  [key: string]: {
    translated_text: string;
    timestamp: number;
  };
}

const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours
let translationCache: TranslationCache = {};

// Load cache from localStorage on init
try {
  const cached = localStorage.getItem("loanease_translation_cache");
  if (cached) {
    translationCache = JSON.parse(cached);
  }
} catch (error) {
  console.warn("Failed to load translation cache:", error);
}

const saveCacheToStorage = () => {
  try {
    localStorage.setItem(
      "loanease_translation_cache",
      JSON.stringify(translationCache)
    );
  } catch (error) {
    console.warn("Failed to save translation cache:", error);
  }
};

export interface TranslationRequest {
  text: string;
  source_language?: string;
  target_language?: string;
}

export interface TranslationResponse {
  translated_text: string;
  source_language: string;
  target_language: string;
  confidence: number;
}

/**
 * Fetch translation from backend with caching.
 * Falls back to original text if service is unavailable.
 */
export const fetchTranslation = async (
  text: string,
  targetLanguage: "en" | "hi" = "hi",
  sourceLanguage: "en" | "hi" = "en",
  translationServiceUrl: string = `${API_BASE_URL}/ai`
): Promise<string> => {
  if (!text || text.trim().length === 0) {
    return text;
  }

  if (sourceLanguage === targetLanguage) {
    return text;
  }

  // Check cache
  const cacheKey = `${sourceLanguage}-${targetLanguage}-${text}`;
  const cached = translationCache[cacheKey];

  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.translated_text;
  }

  try {
    const response = await fetch(`${translationServiceUrl}/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        source_language: sourceLanguage,
        target_language: targetLanguage,
      }),
    });

    if (!response.ok) {
      console.error("Translation API error:", response.statusText);
      return text; // Fallback to original
    }

    const data: TranslationResponse = await response.json();

    // Save to cache
    translationCache[cacheKey] = {
      translated_text: data.translated_text,
      timestamp: Date.now(),
    };
    saveCacheToStorage();

    return data.translated_text;
  } catch (error) {
    console.error("Translation fetch failed:", error);
    return text; // Fallback to original
  }
};

/**
 * Batch translate multiple strings at once.
 */
export const fetchBatchTranslation = async (
  texts: string[],
  targetLanguage: "en" | "hi" = "hi",
  sourceLanguage: "en" | "hi" = "en",
  translationServiceUrl: string = `${API_BASE_URL}/ai`
): Promise<string[]> => {
  const promises = texts.map((text) =>
    fetchTranslation(text, targetLanguage, sourceLanguage, translationServiceUrl)
  );
  return Promise.all(promises);
};

/**
 * Clear translation cache.
 */
export const clearTranslationCache = () => {
  translationCache = {};
  try {
    localStorage.removeItem("loanease_translation_cache");
  } catch (error) {
    console.warn("Failed to clear translation cache:", error);
  }
};
