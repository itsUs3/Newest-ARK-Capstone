import create from 'zustand'

export const useSearchStore = create((set) => ({
  filters: {
    location: '',
    bhk: 'all',
    minPrice: 0,
    maxPrice: 50000000,
  },
  results: [],
  loading: false,

  setFilters: (filters) => set({ filters }),
  setResults: (results) => set({ results }),
  setLoading: (loading) => set({ loading }),
}))

export const usePropertyStore = create((set) => ({
  favorites: [],
  viewed: [],

  addFavorite: (property) =>
    set((state) => ({
      favorites: [...state.favorites, property]
    })),
  removeFavorite: (propertyId) =>
    set((state) => ({
      favorites: state.favorites.filter(p => p.id !== propertyId)
    })),
  addViewed: (property) =>
    set((state) => ({
      viewed: [property, ...state.viewed.slice(0, 9)]
    })),
}))
