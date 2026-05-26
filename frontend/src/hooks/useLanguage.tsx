/**
 * React hook for managing language state and translation.
 */

import { createContext, useContext, useState, useCallback } from "react";

interface LanguageContextType {
  language: "en" | "hi";
  setLanguage: (lang: "en" | "hi") => void;
  t: (key: string, lang?: "en" | "hi") => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(
  undefined
);

export const LanguageProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [language, setLanguage] = useState<"en" | "hi">(
    () => (localStorage.getItem("loanease_language") as "en" | "hi") || "en"
  );

  const handleLanguageChange = useCallback((lang: "en" | "hi") => {
    setLanguage(lang);
    localStorage.setItem("loanease_language", lang);
  }, []);

  const t = useCallback(
    (key: string, lang?: "en" | "hi"): string => {
      const targetLang = lang || language;
      // Placeholder: in real app, fetch from TRANSLATIONS
      return key;
    },
    [language]
  );

  return (
    <LanguageContext.Provider
      value={{ language, setLanguage: handleLanguageChange, t }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
};
