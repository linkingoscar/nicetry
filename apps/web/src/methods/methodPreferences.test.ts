import { beforeEach, describe, expect, it } from 'vitest'

import { readMethodPreferences, recordRecentMethod, toggleFavoriteMethod } from './methodPreferences'

beforeEach(() => localStorage.clear())

describe('method preferences', () => {
  it('keeps favorites and promotes the most recently opened method', () => {
    toggleFavoriteMethod('correlation')
    recordRecentMethod('regression')
    recordRecentMethod('correlation')
    recordRecentMethod('regression')

    expect(readMethodPreferences()).toEqual({
      favorites: ['correlation'],
      recent: ['regression', 'correlation'],
    })
  })
})
