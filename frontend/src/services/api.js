/**
 * Couche service — Toutes les communications avec le backend FastAPI.
 * Chaque fonction correspond à un endpoint REST.
 */
import axios from 'axios'
import { API } from './config.js'

// Instance Axios partagée
const http = axios.create({
  timeout: 60_000,
  headers: { Accept: 'application/json' }
})

// ── Intercepteur : transforme les erreurs Axios en messages lisibles ──────────
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Erreur inconnue'
    return Promise.reject(new Error(
      Array.isArray(detail)
        ? detail.map(e => e.msg).join(' | ')
        : String(detail)
    ))
  }
)

// ═══════════════════════════════════════════════════════════════════════════════
// SANTÉ DU SYSTÈME
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Vérifie l'état de tous les services (IPFS, blockchain, modèle IA).
 * @returns {Promise<{ipfs: boolean, blockchain: boolean, model_loaded: boolean, works_indexed: number}>}
 */
export async function fetchHealth() {
  const { data } = await http.get(API.ENDPOINTS.HEALTH)
  return data
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLUX 1 — ENREGISTREMENT D'UNE ŒUVRE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Enregistre une œuvre musicale dans le pipeline.
 * Étapes : GraFPrint → IPFS → MusicRegistry on-chain.
 *
 * @param {File}     audioFile   Fichier audio WAV ou MP3
 * @param {string}   title       Titre de l'œuvre
 * @param {string}   artist      Artiste principal
 * @param {string[]} recipients  Adresses Ethereum des ayants droit
 * @param {number[]} shares      Parts en % (somme = 100)
 * @param {Function} onProgress  Callback de progression (0-100)
 *
 * @returns {Promise<AudioTrack>}
 */
export async function registerWork(
  audioFile,
  title,
  artist,
  recipients,
  shares,
  onProgress = null
) {
  const formData = new FormData()
  formData.append('file',       audioFile)
  formData.append('title',      title)
  formData.append('artist',     artist)
  formData.append('recipients', JSON.stringify(recipients))
  formData.append('shares',     JSON.stringify(shares))

  const { data } = await http.post(API.ENDPOINTS.REGISTER, formData, {
    headers:         { 'Content-Type': 'multipart/form-data' },
     timeout:          120000,
    onUploadProgress: onProgress
      ? (e) => onProgress(Math.round((e.loaded / e.total) * 100))
      : undefined
  })
  return data
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLUX 1 — DÉTECTION D'UNE COPIE PIRATÉE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Analyse un fichier audio suspect.
 * Flux : extraction GraFPrint → comparaison → [preuve IPFS + certification blockchain]
 *
 * @param {File}     audioFile   Fichier audio suspect
 * @param {Function} onProgress  Callback de progression
 *
 * @returns {Promise<DetectionResponse>}
 *   {match, proof, takedown_request, message}
 */
export async function analyzeAudio(audioFile, onProgress = null) {
  const formData = new FormData()
  formData.append('file', audioFile)

  const { data } = await http.post(API.ENDPOINTS.ANALYZE, formData, {
    headers:         { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
      ? (e) => onProgress(Math.round((e.loaded / e.total) * 100))
      : undefined
  })
  return data
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLUX 2 — SIMULATION DE DISTRIBUTION DES REDEVANCES
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Simule la distribution des redevances pour une œuvre enregistrée.
 * Appelle simulateRoyaltyPayment() dans MusicRegistry et capture
 * les événements PaymentSimulated émis on-chain.
 *
 * @param {string} workHash    Hash SHA-256 de l'empreinte de l'œuvre
 * @param {number} totalAmount Montant fictif total à distribuer
 *
 * @returns {Promise<RoyaltySimulationResponse>}
 *   {tx_hash, work_hash, total_amount, payments, message}
 */
export async function simulateRoyalty(workHash, totalAmount) {
  const { data } = await http.post(API.ENDPOINTS.ROYALTY_SIMULATE, {
    work_hash:    workHash,
    total_amount: totalAmount
  })
  return data
}