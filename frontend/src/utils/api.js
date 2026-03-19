import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Search endpoints
export const searchListings = (params) =>
  apiClient.get('/recommendations', { params })

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

// GNN Floor Plan generation
export const generateGnnFloorplan = (payload) =>
  apiClient.post('/floorplan/generate', payload)

export default apiClient
