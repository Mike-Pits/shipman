import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import i18n, { LANGUAGE_STORAGE_KEY } from '../i18n'
import LanguageToggle from './LanguageToggle'

describe('LanguageToggle', () => {
  it('defaults to English active', () => {
    render(<LanguageToggle />)

    expect(screen.getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'RU' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches i18next to Russian and persists the choice when RU is clicked', async () => {
    const user = userEvent.setup()
    render(<LanguageToggle />)

    await user.click(screen.getByRole('button', { name: 'RU' }))

    expect(i18n.language).toBe('ru')
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('ru')
    expect(screen.getByRole('button', { name: 'RU' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches back to English when EN is clicked', async () => {
    const user = userEvent.setup()
    render(<LanguageToggle />)
    await user.click(screen.getByRole('button', { name: 'RU' }))

    await user.click(screen.getByRole('button', { name: 'EN' }))

    expect(i18n.language).toBe('en')
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('en')
  })
})
