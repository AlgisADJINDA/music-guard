/**
 * Configuration du frontend.
 * BASE_URL pointe vers le proxy Vite en développement,
 * et vers le backend direct en production.
 */
const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const API = {
  BASE_URL,
  ENDPOINTS: {
    HEALTH:           `${BASE_URL}/health`,
    REGISTER:         `${BASE_URL}/register/`,
    ANALYZE:          `${BASE_URL}/analyze/`,
    ROYALTY_SIMULATE: `${BASE_URL}/royalty/simulate`,
  }
}

export default API
