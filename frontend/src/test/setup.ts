import '@testing-library/jest-dom/vitest'
import { beforeEach } from 'vitest'
import i18n from '../i18n'

beforeEach(() => {
  window.localStorage.clear()
  i18n.changeLanguage('en')
})
