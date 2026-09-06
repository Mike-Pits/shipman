import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import ru from './ru.json'

export const LANGUAGE_STORAGE_KEY = 'shipman.language'
export type Language = 'en' | 'ru'

function storedLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return stored === 'ru' ? 'ru' : 'en'
  } catch {
    return 'en'
  }
}

export function setLanguage(language: Language) {
  i18n.changeLanguage(language)
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // localStorage unavailable (e.g. private browsing) — language still
    // switches for this session, it just won't persist across reloads.
  }
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ru: { translation: ru },
  },
  lng: storedLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
