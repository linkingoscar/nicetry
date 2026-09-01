import { useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark'

export function useTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('researchpath_theme')
    return saved === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    localStorage.setItem('researchpath_theme', theme)
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    if (theme === 'dark') {
      root.classList.add('dark-theme')
      document.body.classList.add('dark-theme')
    } else {
      root.classList.remove('dark-theme')
      document.body.classList.remove('dark-theme')
    }
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  return { theme, setTheme, toggleTheme }
}
