import { useTranslation } from 'react-i18next'
import { setLanguage } from '../i18n'

export default function LanguageToggle() {
  const { i18n } = useTranslation()

  return (
    <span>
      <button
        type="button"
        aria-pressed={i18n.language === 'en'}
        disabled={i18n.language === 'en'}
        onClick={() => setLanguage('en')}
      >
        EN
      </button>
      <button
        type="button"
        aria-pressed={i18n.language === 'ru'}
        disabled={i18n.language === 'ru'}
        onClick={() => setLanguage('ru')}
      >
        RU
      </button>
    </span>
  )
}
