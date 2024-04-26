import i18n from 'i18next'
import {initReactI18next} from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import locale_en from './locales/en.json'
import locale_ja from './locales/ja.json'

const STORAGE_KEY = 'i18nextLng'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    returnEmptyString: false,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: STORAGE_KEY,
    },
    resources: {
      en: {
        translation: locale_en
      },
      ja: {
        translation: locale_ja
      }
    },
    interpolation: {
      escapeValue: false
    },
    react: {
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'span']
    }
  })

export default i18n