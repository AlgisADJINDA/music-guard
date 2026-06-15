<template>
  <div class="simul">

    <!-- ── Formulaire ────────────────────────────────────────────────────── -->
    <div class="simul__form">
      <div class="simul__field">
        <label class="simul__label">Hash de l'œuvre</label>
        <input
          v-model="workHash"
          class="simul__input simul__input--mono"
          placeholder="a3f5c7b2d1e9... (64 caractères hex)"
          maxlength="64"
          :class="{ 'simul__input--error': hashError }"
        />
        <span v-if="hashError" class="simul__field-error">
          {{ hashError }}
        </span>
      </div>

      <div class="simul__field">
        <label class="simul__label">
          Montant fictif à distribuer
          <span class="simul__label-hint">(unités arbitraires)</span>
        </label>
        <div class="simul__amount-row">
          <input
            v-model.number="totalAmount"
            type="number"
            min="1"
            class="simul__input"
            placeholder="1000"
            :class="{ 'simul__input--error': amountError }"
          />
          <div class="simul__presets">
            <button
              v-for="preset in [100, 500, 1000, 5000]"
              :key="preset"
              class="simul__preset"
              :class="{ 'simul__preset--active': totalAmount === preset }"
              @click="totalAmount = preset"
            >
              {{ preset }}
            </button>
          </div>
        </div>
        <span v-if="amountError" class="simul__field-error">
          {{ amountError }}
        </span>
      </div>

      <button
        class="simul__btn"
        :disabled="loading || !canSubmit"
        @click="submit"
      >
        <span v-if="loading" class="simul__spinner" />
        <span v-else>Simuler la distribution</span>
      </button>
    </div>

    <!-- ── Résultats ──────────────────────────────────────────────────────── -->
    <div v-if="result" class="simul__result">

      <!-- En-tête résultat -->
      <div class="simul__result-header">
        <div class="simul__result-title">Résultat de simulation</div>
        <code class="simul__tx">Tx : {{ truncate(result.tx_hash) }}</code>
      </div>

      <!-- Statistiques -->
      <div class="simul__stats">
        <div class="simul__stat">
          <span class="simul__stat-label">Montant total</span>
          <span class="simul__stat-val">{{ result.total_amount.toLocaleString() }}</span>
        </div>
        <div class="simul__stat">
          <span class="simul__stat-label">Bénéficiaires</span>
          <span class="simul__stat-val">{{ result.payments.length }}</span>
        </div>
        <div class="simul__stat">
          <span class="simul__stat-label">Total distribué</span>
          <span class="simul__stat-val" :class="totalOk ? 'ok' : 'error'">
            {{ totalDistributed.toLocaleString() }}
          </span>
        </div>
      </div>

      <!-- Barres de distribution -->
      <div class="simul__bars">
        <div
          v-for="(p, i) in result.payments"
          :key="i"
          class="simul__bar-row"
        >
          <div class="simul__bar-info">
            <code class="simul__addr">{{ truncate(p.beneficiary, 12) }}</code>
            <span class="simul__bar-pct">{{ pct(p.amount) }}%</span>
            <span class="simul__bar-amount">
              {{ p.amount.toLocaleString() }} unités
            </span>
          </div>
          <div class="simul__bar-track">
            <div
              class="simul__bar-fill"
              :style="{
                width: pct(p.amount) + '%',
                background: barColor(i)
              }"
            />
          </div>
        </div>
      </div>

      <!-- Message -->
      <p class="simul__message">{{ result.message }}</p>

      <!-- Note académique -->
      <div class="simul__note">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>
          Aucun transfert réel effectué. Les événements
          <code>PaymentSimulated</code> sont émis on-chain et
          consultables via Ganache. Cette simulation démontre la
          faisabilité d'une distribution automatisée et transparente
          (Ciriello et al., 2023 ; Pan et al., 2024).
        </p>
      </div>
    </div>

    <!-- ── Erreur ──────────────────────────────────────────────────────────── -->
    <div v-if="error" class="simul__error">
      <strong>Erreur</strong> — {{ error }}
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { simulateRoyalty } from '@/services/api.js'

// ── Props ─────────────────────────────────────────────────────────────────────
const props = defineProps({
  prefillHash: { type: String, default: '' }
})

// ── State ─────────────────────────────────────────────────────────────────────
const workHash    = ref(props.prefillHash)
const totalAmount = ref(1000)
const loading     = ref(false)
const result      = ref(null)
const error       = ref('')

// ── Validation ────────────────────────────────────────────────────────────────
const hashError = computed(() => {
  if (!workHash.value) return ''
  if (workHash.value.length !== 64) return 'Le hash doit faire exactement 64 caractères.'
  if (!/^[0-9a-fA-F]+$/.test(workHash.value)) return 'Caractères hexadécimaux uniquement.'
  return ''
})

const amountError = computed(() => {
  if (!totalAmount.value) return ''
  if (totalAmount.value <= 0) return 'Le montant doit être supérieur à 0.'
  return ''
})

const canSubmit = computed(() =>
  workHash.value.length === 64 &&
  !hashError.value &&
  totalAmount.value > 0 &&
  !amountError.value
)

const totalDistributed = computed(() =>
  result.value?.payments.reduce((s, p) => s + p.amount, 0) ?? 0
)

const totalOk = computed(() =>
  result.value && totalDistributed.value === result.value.total_amount
)

// ── Actions ───────────────────────────────────────────────────────────────────
async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value   = ''
  result.value  = null

  try {
    result.value = await simulateRoyalty(workHash.value, totalAmount.value)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function pct(amount) {
  if (!result.value?.total_amount) return 0
  return ((amount / result.value.total_amount) * 100).toFixed(1)
}

function truncate(str, n = 16) {
  if (!str) return '—'
  return str.length > n * 2 ? `${str.slice(0, n)}...${str.slice(-6)}` : str
}

const BAR_COLORS = ['#4f7cff', '#00e5a0', '#fbbf24', '#f472b6', '#a78bfa']
function barColor(i) { return BAR_COLORS[i % BAR_COLORS.length] }
</script>

<style scoped>
.simul { display: flex; flex-direction: column; gap: 24px; }

.simul__form {
  background:    var(--card);
  border:        1px solid var(--border);
  border-radius: 12px;
  padding:       24px;
  display:       flex;
  flex-direction: column;
  gap:           20px;
}
.simul__field { display: flex; flex-direction: column; gap: 6px; }
.simul__label {
  font-size:   0.82rem;
  font-weight: 600;
  color:       var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.simul__label-hint {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
.simul__input {
  background:    var(--surface);
  border:        1.5px solid var(--border);
  border-radius: 8px;
  padding:       10px 14px;
  color:         var(--text);
  font-size:     0.9rem;
  font-family:   inherit;
  outline:       none;
  transition:    border-color 0.2s;
  width:         100%;
  box-sizing:    border-box;
}
.simul__input:focus       { border-color: var(--accent); }
.simul__input--mono       { font-family: var(--mono); font-size: 0.82rem; }
.simul__input--error      { border-color: var(--red); }
.simul__field-error       { font-size: 0.78rem; color: var(--red); }

.simul__amount-row {
  display:     flex;
  gap:         10px;
  align-items: center;
  flex-wrap:   wrap;
}
.simul__amount-row .simul__input { flex: 1; min-width: 100px; }
.simul__presets { display: flex; gap: 6px; flex-wrap: wrap; }
.simul__preset {
  padding:       5px 12px;
  border:        1px solid var(--border);
  border-radius: 6px;
  background:    var(--surface);
  color:         var(--muted);
  font-size:     0.8rem;
  font-family:   var(--mono);
  cursor:        pointer;
  transition:    all 0.15s;
}
.simul__preset:hover,
.simul__preset--active {
  border-color: var(--accent);
  color:        var(--accent);
  background:   color-mix(in srgb, var(--accent) 8%, var(--surface));
}
.simul__btn {
  padding:       12px 24px;
  background:    var(--green);
  color:         #000;
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
.simul__btn:disabled { opacity: 0.45; cursor: not-allowed; }
.simul__spinner {
  width:         18px;
  height:        18px;
  border:        2px solid rgba(0,0,0,0.3);
  border-top-color: #000;
  border-radius: 50%;
  animation:     spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Résultats ─────────────────────────────────────────────────────────── */
.simul__result {
  background:    var(--card);
  border:        1.5px solid var(--green);
  border-radius: 12px;
  padding:       24px;
  display:       flex;
  flex-direction: column;
  gap:           20px;
}
.simul__result-header {
  display:         flex;
  justify-content: space-between;
  align-items:     center;
  flex-wrap:       wrap;
  gap:             8px;
}
.simul__result-title { font-size: 1rem; font-weight: 700; color: var(--green); }
.simul__tx {
  font-family: var(--mono);
  font-size:   0.75rem;
  color:       var(--muted);
  background:  var(--surface);
  padding:     3px 8px;
  border-radius: 4px;
}
.simul__stats {
  display:               grid;
  grid-template-columns: repeat(3, 1fr);
  gap:                   10px;
}
.simul__stat {
  background:    var(--surface);
  border:        1px solid var(--border);
  border-radius: 8px;
  padding:       12px;
  display:       flex;
  flex-direction: column;
  gap:           4px;
  text-align:    center;
}
.simul__stat-label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; }
.simul__stat-val   { font-size: 1.2rem; font-weight: 700; color: var(--text); font-family: var(--mono); }
.simul__stat-val.ok    { color: var(--green); }
.simul__stat-val.error { color: var(--red); }

.simul__bars { display: flex; flex-direction: column; gap: 14px; }
.simul__bar-row { display: flex; flex-direction: column; gap: 6px; }
.simul__bar-info {
  display:     flex;
  align-items: center;
  gap:         12px;
  flex-wrap:   wrap;
}
.simul__addr {
  font-family: var(--mono);
  font-size:   0.78rem;
  color:       var(--accent);
  flex:        1;
  min-width:   140px;
}
.simul__bar-pct    { font-size: 0.85rem; font-weight: 700; color: var(--text); min-width: 40px; }
.simul__bar-amount { font-size: 0.78rem; color: var(--muted); font-family: var(--mono); }
.simul__bar-track {
  height:        8px;
  background:    var(--surface);
  border-radius: 99px;
  overflow:      hidden;
}
.simul__bar-fill {
  height:        100%;
  border-radius: 99px;
  transition:    width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.simul__message { font-size: 0.85rem; color: var(--muted); margin: 0; }
.simul__note {
  display:    flex;
  gap:        10px;
  background: color-mix(in srgb, var(--accent) 5%, var(--surface));
  border:     1px solid var(--border);
  border-radius: 8px;
  padding:    14px;
}
.simul__note svg { width: 18px; height: 18px; color: var(--accent); flex-shrink: 0; margin-top: 1px; }
.simul__note p   { font-size: 0.8rem; color: var(--muted); margin: 0; line-height: 1.5; }
.simul__note code { font-family: var(--mono); color: var(--accent); }

.simul__error {
  background:    color-mix(in srgb, var(--red) 8%, var(--card));
  border:        1px solid var(--red);
  border-radius: 8px;
  padding:       14px 18px;
  color:         var(--red);
  font-size:     0.88rem;
}
</style>