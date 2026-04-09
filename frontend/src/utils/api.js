import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 second timeout
})

// Search endpoints
export const searchListings = (data) =>
  apiClient.post('/recommendations', data)

export const getListings = (location, limit) =>
  apiClient.get('/data/listings', { params: { location, limit } })

export const getLocations = () =>
  apiClient.get('/data/locations')

// Price prediction
export const predictPrice = (data) =>
  apiClient.post('/price/predict', data)

export const getMarketAnalysis = (location) =>
  apiClient.get(`/price/market-analysis/${location}`)

// Fraud detection
export const detectFraud = (data) =>
  apiClient.post('/fraud/detect', data)

export const batchDetectFraud = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/fraud/batch-detect', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// GenAI endpoints
export const generateDescription = (property) =>
  apiClient.post('/genai/describe', property)

export const explainPrice = (data) =>
  apiClient.post('/genai/explain-price', data)

export const chatWithAdvisor = (message) =>
  apiClient.post('/genai/chat', { message })

export const getTrendingLocations = (topN = 5) =>
  apiClient.get('/genai/trending-locations', { params: { top_n: topN } })

export const getCrossModalMatches = (payload) =>
  apiClient.post('/genai/cross-modal-match', payload)

export const getMarketAlerts = (location, params = {}) =>
  apiClient.get(`/genai/market-alerts/${encodeURIComponent(location)}`, { params })

export const getMarketInsights = (location) =>
  apiClient.get(`/genai/market-insights/${encodeURIComponent(location)}`)

export const getSocialAnalysis = async (area, params = {}) => {
  console.log('[API] getSocialAnalysis called with area:', area, 'params:', params)
  try {
    const response = await apiClient.get('/social-analysis', { params: { area, ...params } })
    console.log('[API] getSocialAnalysis response:', response)
    return response
  } catch (error) {
    console.error('[API] getSocialAnalysis error:', error)
    throw error
  }
}

export const getInvestmentForecast = (payload) =>
  apiClient.post('/genai/investment-forecast', payload)

export const analyzeContract = (payload) =>
  apiClient.post('/genai/contract-analyze', payload)

export const compareListings = (payload) =>
  apiClient.post('/compare', payload)

export const enrichPropertyDetail = (payload) =>
  apiClient.post('/properties/enrich', payload)

// Location Booster - Neighborhood Report
export const getNeighborhoodReport = (location) =>
  apiClient.post('/genai/neighborhood-report', { location })

// Amenity Matcher - Lifestyle to Amenity Matching
export const getAmenityMatch = (lifestyle, location = '') =>
  apiClient.post('/genai/amenity-match', { lifestyle, location })

export const getLifestyleProfiles = () =>
  apiClient.get('/genai/lifestyle-profiles')

// Vastu Checker - Vastu/Feng Shui Compliance
export const checkVastuCompliance = (data) =>
  apiClient.post('/vastu/check', data)

// Data management
export const uploadListings = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/data/upload-listings', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export default apiClient
