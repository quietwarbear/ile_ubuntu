import React, { createContext, useContext, useState, useCallback } from 'react';
import en from './en';
import es from './es';
import yo from './yo';

const translations = { en, es, yo };
const LANG_NAMES = { en: 'English', es: 'Español', yo: 'Yorùbá' };

const I18nContext = createContext();

export function I18nProvider({ children, defaultLang = 'en' }) {
  const [lang, setLang] = useState(defaultLang);

  const t = useCallback((key) => {
    return translations[lang]?.[key] || translations.en?.[key] || key;
  }, [lang]);

  return (
    <I18nContext.Provider value={{ lang, setLang, t, LANG_NAMES }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
