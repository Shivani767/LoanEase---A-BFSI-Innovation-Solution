/**
 * Language Switcher Component
 * Compact pill buttons for EN/HI selection.
 * Non-intrusive overlay in chat window.
 */

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { TRANSLATIONS } from "@/lib/translations";
import { detectLanguage } from "@/lib/languageUtils";

interface LanguageSwitcherProps {
  currentLanguage: "en" | "hi";
  onLanguageChange: (lang: "en" | "hi") => void;
}

export const LanguageSwitcher = ({
  currentLanguage,
  onLanguageChange,
}: LanguageSwitcherProps) => {
  const [isAutoDetecting, setIsAutoDetecting] = useState(false);

  const handleLanguageClick = (lang: "en" | "hi") => {
    if (lang !== currentLanguage) {
      onLanguageChange(lang);
      const message =
        lang === "en"
          ? TRANSLATIONS.language_switched_en
          : TRANSLATIONS.language_switched_hi;
      toast.success(message);
    }
  };

  const handleAutoDetect = async (text: string) => {
    if (!text || text.length < 5 || isAutoDetecting) return;

    setIsAutoDetecting(true);
    try {
      const result = await detectLanguage(text);
      if (result.language !== "unknown" && result.language !== currentLanguage) {
        onLanguageChange(result.language);
        const message =
          result.language === "en"
            ? TRANSLATIONS.language_detected_en
            : TRANSLATIONS.language_detected_hi;
        toast.info(message);
      }
    } catch (error) {
      console.error("Auto-detect error:", error);
    } finally {
      setIsAutoDetecting(false);
    }
  };

  return (
    <div className="flex items-center gap-2 bg-yellow-500/10 rounded-full p-1 border border-yellow-500/20">
      <button
        onClick={() => handleLanguageClick("en")}
        className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
          currentLanguage === "en"
            ? "bg-yellow-500 text-black"
            : "text-gray-600 hover:text-gray-800"
        }`}
      >
        EN
      </button>
      <div className="w-px h-4 bg-yellow-500/20" />
      <button
        onClick={() => handleLanguageClick("hi")}
        className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
          currentLanguage === "hi"
            ? "bg-yellow-500 text-black"
            : "text-gray-600 hover:text-gray-800"
        }`}
      >
        हि
      </button>
    </div>
  );
};
