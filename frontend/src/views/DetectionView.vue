<template>
  <div class="detection">

    <div class="page-header">
      <router-link class="page-back" to="/">← Accueil</router-link>
      <h1 class="page-title">
        <span class="page-title__badge page-title__badge--red">Flux 1</span>
        Détection & Certification
      </h1>
      <p class="page-desc">
        Enregistrez une œuvre originale, puis soumettez un fichier suspect
        pour comparer les empreintes GraFPrint et certifier la preuve on-chain.
      </p>
    </div>

    <!-- ── Onglets ────────────────────────────────────────────────────────── -->
    <div class="tabs">
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'register' }"
        @click="activeTab = 'register'"
      >
        <span class="tab__num">1</span> Enregistrer une œuvre
      </button>
      <div class="tabs__sep">→</div>
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'detect' }"
        @click="activeTab = 'detect'"
      >
        <span class="tab__num">2</span> Détecter une copie
      </button>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         ONGLET 1 — ENREGISTREMENT
    ═══════════════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'register'" class="panel">
      <div class="panel__header">
        <div class="panel__title">Enregistrement d'une œuvre originale</div>
        <div class="panel__desc">
          Extrait l'empreinte GraFPrint, stocke sur IPFS et enregistre
          dans <code>MusicRegistry</code> on-chain.
        </div>
      </div>

      <div class="panel__body">
        <!-- Fichier audio -->
        <UploadAudio
          label="Fichier audio original (WAV ou MP3)"
          :progress="registerProgress"
          @file-selected="registerFile = $event"
          @file-cleared="registerFile = null"
        />

        <!-- Métadonnées -->
        <div class="form-grid">
          <div class="form-field">
            <label class="form-label">Titre de l'œuvre</label>
            <input
              v-model="regTitle"
              class="form-input"
              placeholder="Ma Chanson"
            />
          </div>
          <div class="form-field">
            <label class="form-label">Artiste principal</label>
            <input
              v-model="regArtist"
              class="form-input"
              placeholder="Artiste A"
            />
          </div>
        </div>

        <!-- Ayants droit -->
        <div class="form-field">
          <label class="form-label">
            Ayants droit
            <button class="add-btn" @click="addRecipient">+ Ajouter</button>
          </label>
          <div class="recipients">
            <div
              v-for="(r, i) in recipients"
              :key="i"
              class="recipient-row"
            >
              <input
                v-model="r.address"
                class="form-input form-input--mono"
                :placeholder="`Adresse Ethereum ${i + 1} (0x...)`"
              />
              <input
                v-model.number="r.share"
                type="number"
                min="1"
                max="100"
                class="form-input form-input--share"
                placeholder="%"
              />
              <button
                v-if="recipients.length > 1"
                class="remove-btn"
                @click="removeRecipient(i)"
              >×</button>
            </div>
            <div
              class="shares-total"
              :class="{ 'shares-total--ok': sharesTotal === 100,
                        'shares-total--error': sharesTotal !== 100 }"
            >
              Total des parts : {{ sharesTotal }}% {{ sharesTotal === 100 ? '✓' : '≠ 100' }}
            </div>
          </div>
        </div>

        <!-- Bouton -->
        <button
          class="btn-primary"
          :disabled="!canRegister || registerLoading"
          @click="doRegister"
        >
          <span v-if="registerLoading" class="spinner" />
          <span v-else>Enregistrer l'œuvre</span>
        </button>

        <!-- Erreur -->
        <div v-if="registerError" class="error-box">{{ registerError }}</div>

        <!-- Succès -->
        <div v-if="registerResult" class="success-box">
          <div class="success-box__title">✓ Œuvre enregistrée avec succès</div>
          <div class="kv-list">
            <div class="kv"><span>Titre</span><code>{{ registerResult.title }}</code></div>
            <div class="kv"><span>Artiste</span><code>{{ registerResult.artist }}</code></div>
            <div class="kv"><span>Hash empreinte</span><code class="hash">{{ registerResult.fingerprint_hash }}</code></div>
            <div class="kv"><span>CID IPFS</span><code>{{ registerResult.ipfs_cid }}</code></div>
            <div class="kv"><span>Tx blockchain</span><code class="hash">{{ registerResult.tx_hash }}</code></div>
          </div>
          <button class="link-btn" @click="goToDetect">
            → Tester la détection avec ce hash
          </button>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════════════
         ONGLET 2 — DÉTECTION
    ═══════════════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'detect'" class="panel">
      <div class="panel__header">
        <div class="panel__title">Analyse d'un fichier suspect</div>
        <div class="panel__desc">
          Compare les empreintes, génère une preuve certifiée on-chain
          et simule la notification DMCA.
        </div>
      </div>

      <div class="panel__body">
        <UploadAudio
          label="Fichier audio suspect (WAV ou MP3)"
          :progress="detectProgress"
          @file-selected="detectFile = $event"
          @file-cleared="detectFile = null"
        />

        <button
          class="btn-detect"
          :disabled="!detectFile || detectLoading"
          @click="doDetect"
        >
          <span v-if="detectLoading" class="spinner" />
          <span v-else>Analyser le fichier</span>
        </button>

        <!-- Étapes de progression -->
        <div v-if="detectLoading" class="steps-progress">
          <div
            v-for="(step, i) in detectSteps"
            :key="i"
            class="step-item"
            :class="{
              'step-item--active':   i === currentDetectStep,
              'step-item--done':     i < currentDetectStep,
              'step-item--pending':  i > currentDetectStep
            }"
          >
            <span class="step-dot" />
            {{ step }}
          </div>
        </div>

        <!-- Erreur -->
        <div v-if="detectError" class="error-box">{{ detectError }}</div>

        <!-- Résultat -->
        <AlerteDetection :result="detectResult" />
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import UploadAudio       from '@/components/UploadAudio.vue'
import AlerteDetection   from '@/components/AlerteDetection.vue'
import { registerWork, analyzeAudio } from '@/services/api.js'

// ── Tabs ──────────────────────────────────────────────────────────────────────
const activeTab = ref('register')

// ═══════════════════════════════════════════════════════════════════════════════
// ENREGISTREMENT
// ═══════════════════════════════════════════════════════════════════════════════
const registerFile     = ref(null)
const regTitle         = ref('')
const regArtist        = ref('')
const recipients       = ref([{ address: '', share: 100 }])
const registerProgress = ref(0)
const registerLoading  = ref(false)
const registerError    = ref('')
const registerResult   = ref(null)

const sharesTotal = computed(() =>
  recipients.value.reduce((s, r) => s + (Number(r.share) || 0), 0)
)

const canRegister = computed(() =>
  registerFile.value &&
  regTitle.value.trim() &&
  regArtist.value.trim() &&
  sharesTotal.value === 100 &&
  recipients.value.every(r => r.address.startsWith('0x') && r.address.length >= 10)
)

function addRecipient() {
  recipients.value.push({ address: '', share: 0 })
}
function removeRecipient(i) {
  recipients.value.splice(i, 1)
}

async function doRegister() {
  if (!canRegister.value) return
  registerLoading.value = true
  registerError.value   = ''
  registerResult.value  = null

  try {
    registerResult.value = await registerWork(
      registerFile.value,
      regTitle.value,
      regArtist.value,
      recipients.value.map(r => r.address),
      recipients.value.map(r => Number(r.share)),
      (p) => { registerProgress.value = p }
    )
  } catch (e) {
    registerError.value = e.message
  } finally {
    registerLoading.value  = false
    registerProgress.value = 0
  }
}

function goToDetect() {
  activeTab.value = 'detect'
}

// ═══════════════════════════════════════════════════════════════════════════════
// DÉTECTION
// ═══════════════════════════════════════════════════════════════════════════════
const detectFile    = ref(null)
const detectProgress = ref(0)
const detectLoading = ref(false)
const detectError   = ref('')
const detectResult  = ref(null)
const currentDetectStep = ref(-1)

const detectSteps = [
  'Upload du fichier...',
  'Extraction de l\'empreinte GraFPrint...',
  'Comparaison dans l\'index...',
  'Certification de la preuve on-chain...',
  'Simulation notification DMCA...'
]

async function doDetect() {
  if (!detectFile.value) return
  detectLoading.value = true
  detectError.value   = ''
  detectResult.value  = null
  currentDetectStep.value = 0

  const stepTimer = setInterval(() => {
    if (currentDetectStep.value < detectSteps.length - 1) {
      currentDetectStep.value++
    }
  }, 1200)

  try {
    detectResult.value = await analyzeAudio(
      detectFile.value,
      (p) => { detectProgress.value = p }
    )
  } catch (e) {
    detectError.value = e.message
  } finally {
    clearInterval(stepTimer)
    detectLoading.value       = false
    detectProgress.value      = 0
    currentDetectStep.value   = -1
  }
}
</script>

<style scoped>
.detection { display: flex; flex-direction: column; gap: 28px; }

.page-header { display: flex; flex-direction: column; gap: 8px; }
.page-back {
  font-size:   0.82rem;
  color:       var(--muted);
  text-decoration: none;
}
.page-back:hover { color: var(--accent); }
.page-title {
  font-size:   1.8rem;
  font-weight: 800;
  color:       var(--text);
  display:     flex;
  align-items: center;
  gap:         12px;
  flex-wrap:   wrap;
}
.page-title__badge {
  font-size:     0.72rem;
  padding:       4px 10px;
  border-radius: 99px;
  font-family:   var(--mono);
  font-weight:   700;
}
.page-title__badge--red { background: color-mix(in srgb, var(--red) 15%, transparent); color: var(--red); }
.page-desc { font-size: 0.88rem; color: var(--muted); line-height: 1.6; }

/* Tabs */
.tabs {
  display:     flex;
  align-items: center;
  gap:         8px;
  flex-wrap:   wrap;
}
.tab {
  padding:       10px 20px;
  border:        1.5px solid var(--border);
  border-radius: 8px;
  background:    var(--card);
  color:         var(--muted);
  font-size:     0.88rem;
  font-family:   inherit;
  font-weight:   600;
  cursor:        pointer;
  display:       flex;
  align-items:   center;
  gap:           8px;
  transition:    all 0.2s;
}
.tab:hover      { border-color: var(--accent); color: var(--text); }
.tab--active    { border-color: var(--accent); color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, var(--card)); }
.tab__num {
  width:           22px;
  height:          22px;
  border-radius:   50%;
  background:      var(--border);
  display:         flex;
  align-items:     center;
  justify-content: center;
  font-size:       0.75rem;
}
.tab--active .tab__num { background: var(--accent); color: #fff; }
.tabs__sep { color: var(--muted); font-size: 1rem; }

/* Panel */
.panel {
  background:    var(--card);
  border:        1px solid var(--border);
  border-radius: 12px;
  overflow:      hidden;
}
.panel__header {
  padding:     20px 24px;
  border-bottom: 1px solid var(--border);
  background:  var(--surface);
}
.panel__title { font-size: 1rem; font-weight: 700; color: var(--text); }
.panel__desc  { font-size: 0.82rem; color: var(--muted); margin-top: 4px; line-height: 1.5; }
.panel__desc code { font-family: var(--mono); color: var(--accent); }
.panel__body  { padding: 24px; display: flex; flex-direction: column; gap: 20px; }

/* Form */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
.form-field { display: flex; flex-direction: column; gap: 6px; }
.form-label {
  font-size:   0.78rem;
  font-weight: 600;
  color:       var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display:     flex;
  align-items: center;
  justify-content: space-between;
}
.form-input {
  background:    var(--surface);
  border:        1.5px solid var(--border);
  border-radius: 8px;
  padding:       10px 14px;
  color:         var(--text);
  font-size:     0.9rem;
  font-family:   inherit;
  outline:       none;
  transition:    border-color 0.2s;
  box-sizing:    border-box;
  width:         100%;
}
.form-input:focus  { border-color: var(--accent); }
.form-input--mono  { font-family: var(--mono); font-size: 0.8rem; }
.form-input--share { width: 70px; flex-shrink: 0; text-align: center; }

.add-btn {
  background:  none;
  border:      1px solid var(--border);
  color:       var(--accent);
  font-size:   0.72rem;
  padding:     2px 8px;
  border-radius: 4px;
  cursor:      pointer;
}
.recipients { display: flex; flex-direction: column; gap: 8px; }
.recipient-row { display: flex; gap: 8px; align-items: center; }
.remove-btn {
  background:    none;
  border:        1px solid var(--border);
  color:         var(--red);
  width:         28px;
  height:        28px;
  border-radius: 4px;
  font-size:     1rem;
  cursor:        pointer;
  flex-shrink:   0;
  display:       flex;
  align-items:   center;
  justify-content: center;
}
.shares-total {
  font-size:   0.8rem;
  font-family: var(--mono);
  padding:     6px 10px;
  border-radius: 6px;
  border:      1px solid var(--border);
  background:  var(--surface);
}
.shares-total--ok    { color: var(--green); border-color: color-mix(in srgb, var(--green) 30%, var(--border)); }
.shares-total--error { color: var(--red); border-color: color-mix(in srgb, var(--red) 30%, var(--border)); }

/* Boutons d'action */
.btn-primary, .btn-detect {
  padding:       12px 24px;
  border:        none;
  border-radius: 8px;
  font-size:     0.92rem;
  font-weight:   700;
  font-family:   inherit;
  cursor:        pointer;
  display:       flex;
  align-items:   center;
  justify-content: center;
  gap:           8px;
  transition:    opacity 0.2s;
}
.btn-primary { background: var(--accent); color: #fff; }
.btn-detect  { background: var(--red); color: #fff; }
.btn-primary:disabled,
.btn-detect:disabled { opacity: 0.45; cursor: not-allowed; }
.spinner {
  width:         18px;
  height:        18px;
  border:        2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation:     spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Steps de progression */
.steps-progress { display: flex; flex-direction: column; gap: 6px; }
.step-item {
  display:     flex;
  align-items: center;
  gap:         10px;
  font-size:   0.82rem;
  color:       var(--muted);
  transition:  all 0.3s;
}
.step-item--active { color: var(--accent); font-weight: 600; }
.step-item--done   { color: var(--green); }
.step-dot {
  width:         8px;
  height:        8px;
  border-radius: 50%;
  background:    var(--border);
  flex-shrink:   0;
}
.step-item--active .step-dot { background: var(--accent); animation: pulse 1s infinite; }
.step-item--done   .step-dot { background: var(--green); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* Boxes */
.error-box {
  background:    color-mix(in srgb, var(--red) 8%, var(--surface));
  border:        1px solid var(--red);
  border-radius: 8px;
  padding:       12px 16px;
  color:         var(--red);
  font-size:     0.88rem;
}
.success-box {
  background:    color-mix(in srgb, var(--green) 6%, var(--surface));
  border:        1.5px solid var(--green);
  border-radius: 10px;
  padding:       20px;
  display:       flex;
  flex-direction: column;
  gap:           12px;
}
.success-box__title { font-size: 0.95rem; font-weight: 700; color: var(--green); }
.kv-list { display: flex; flex-direction: column; gap: 6px; }
.kv {
  display:   flex;
  gap:       12px;
  font-size: 0.82rem;
  flex-wrap: wrap;
  align-items: flex-start;
}
.kv span   { color: var(--muted); min-width: 120px; flex-shrink: 0; }
.kv code   { font-family: var(--mono); color: var(--accent); word-break: break-all; }
.kv .hash  { font-size: 0.75rem; }
.link-btn {
  background:  none;
  border:      none;
  color:       var(--accent);
  font-size:   0.85rem;
  cursor:      pointer;
  text-align:  left;
  padding:     0;
  text-decoration: underline;
}
</style>