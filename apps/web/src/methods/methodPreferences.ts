const KEY = 'researchpath.method-preferences.v1'
const MAX_RECENT = 12

export interface MethodPreferences {
  favorites: string[]
  recent: string[]
}

const empty = (): MethodPreferences => ({ favorites: [], recent: [] })

export function readMethodPreferences(): MethodPreferences {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw || raw.length > 20_000) return empty()
    const value = JSON.parse(raw) as Partial<MethodPreferences>
    if (!Array.isArray(value.favorites) || !Array.isArray(value.recent)) return empty()
    return {
      favorites: value.favorites.filter((item): item is string => typeof item === 'string'),
      recent: value.recent.filter((item): item is string => typeof item === 'string').slice(0, MAX_RECENT),
    }
  } catch {
    return empty()
  }
}

function write(preferences: MethodPreferences): MethodPreferences {
  try {
    localStorage.setItem(KEY, JSON.stringify(preferences))
    return preferences
  } catch {
    return readMethodPreferences()
  }
}

export function recordRecentMethod(methodId: string): MethodPreferences {
  const current = readMethodPreferences()
  return write({ ...current, recent: [methodId, ...current.recent.filter((id) => id !== methodId)].slice(0, MAX_RECENT) })
}

export function toggleFavoriteMethod(methodId: string): MethodPreferences {
  const current = readMethodPreferences()
  const favorites = current.favorites.includes(methodId)
    ? current.favorites.filter((id) => id !== methodId)
    : [...current.favorites, methodId]
  return write({ ...current, favorites })
}
