"use client";

import * as React from "react";
import { Languages, Check } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// EU Languages as per FR-006 requirement
const EU_LANGUAGES = [
  { code: "bg", name: "Български", nativeName: "Bulgarian" },
  { code: "cs", name: "Čeština", nativeName: "Czech" },
  { code: "da", name: "Dansk", nativeName: "Danish" },
  { code: "de", name: "Deutsch", nativeName: "German" },
  { code: "el", name: "Ελληνικά", nativeName: "Greek" },
  { code: "en", name: "English", nativeName: "English" },
  { code: "es", name: "Español", nativeName: "Spanish" },
  { code: "et", name: "Eesti", nativeName: "Estonian" },
  { code: "fi", name: "Suomi", nativeName: "Finnish" },
  { code: "fr", name: "Français", nativeName: "French" },
  { code: "ga", name: "Gaeilge", nativeName: "Irish" },
  { code: "hr", name: "Hrvatski", nativeName: "Croatian" },
  { code: "hu", name: "Magyar", nativeName: "Hungarian" },
  { code: "it", name: "Italiano", nativeName: "Italian" },
  { code: "lt", name: "Lietuvių", nativeName: "Lithuanian" },
  { code: "lv", name: "Latviešu", nativeName: "Latvian" },
  { code: "mt", name: "Malti", nativeName: "Maltese" },
  { code: "nl", name: "Nederlands", nativeName: "Dutch" },
  { code: "pl", name: "Polski", nativeName: "Polish" },
  { code: "pt", name: "Português", nativeName: "Portuguese" },
  { code: "ro", name: "Română", nativeName: "Romanian" },
  { code: "sk", name: "Slovenčina", nativeName: "Slovak" },
  { code: "sl", name: "Slovenščina", nativeName: "Slovenian" },
  { code: "sv", name: "Svenska", nativeName: "Swedish" },
];

interface LanguageSelectorProps {
  value?: string;
  onValueChange?: (language: string) => void;
  showFlag?: boolean;
  variant?: "dropdown" | "compact";
  className?: string;
}

export function LanguageSelector({
  value = "de",
  onValueChange,
  showFlag = true,
  variant = "dropdown",
  className,
}: LanguageSelectorProps) {
  const [selectedLanguage, setSelectedLanguage] = React.useState(value);

  React.useEffect(() => {
    setSelectedLanguage(value);
  }, [value]);

  const handleLanguageChange = (newLanguage: string) => {
    setSelectedLanguage(newLanguage);
    onValueChange?.(newLanguage);

    // Optionally persist to localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("preferred-language", newLanguage);
    }
  };

  const getCurrentLanguage = () => {
    return (
      EU_LANGUAGES.find((lang) => lang.code === selectedLanguage) ||
      EU_LANGUAGES.find((lang) => lang.code === "en")!
    );
  };

  if (variant === "compact") {
    return (
      <button
        onClick={() => {
          // Cycle through primary languages (DE/EN)
          const currentIndex = selectedLanguage === "de" ? 0 : 1;
          const nextLang = currentIndex === 0 ? "en" : "de";
          handleLanguageChange(nextLang);
        }}
        className={cn(
          "inline-flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent transition-colors",
          className
        )}
      >
        <Languages className="h-4 w-4" />
        <span className="text-sm font-medium">
          {getCurrentLanguage().code.toUpperCase()}
        </span>
      </button>
    );
  }

  return (
    <Select value={selectedLanguage} onValueChange={handleLanguageChange}>
      <SelectTrigger className={cn("w-[200px]", className)}>
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4" />
          <SelectValue>
            {getCurrentLanguage().name}
          </SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {EU_LANGUAGES.map((language) => (
          <SelectItem
            key={language.code}
            value={language.code}
            className="cursor-pointer"
          >
            <div className="flex items-center justify-between w-full gap-2">
              <span>{language.name}</span>
              {language.code === selectedLanguage && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// Hook for using language in components
export function useLanguage() {
  const [language, setLanguage] = React.useState("de");

  React.useEffect(() => {
    // Try to get from localStorage first
    const stored =
      typeof window !== "undefined"
        ? localStorage.getItem("preferred-language")
        : null;

    if (stored && EU_LANGUAGES.some((lang) => lang.code === stored)) {
      setLanguage(stored);
    } else {
      // Fallback to browser language
      const browserLang = navigator.language.split("-")[0];
      const supported = EU_LANGUAGES.some((lang) => lang.code === browserLang);
      setLanguage(supported ? browserLang : "de");
    }
  }, []);

  return { language, setLanguage };
}
