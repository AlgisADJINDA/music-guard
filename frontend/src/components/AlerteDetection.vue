<template>
  <div v-if="result" class="alerte" :class="alerteClass">

    <!-- ── En-tête ──────────────────────────────────────────────────────── -->
    <div class="alerte__header">
      <div class="alerte__badge">
        <span class="alerte__dot" />
        {{ result.match.is_match ? '⚠ PIRATERIE DÉTECTÉE' : '✓ CONTENU LÉGAL' }}
      </div>
      <span class="alerte__score">
        Score : {{ (result.match.score * 100).toFixed(2) }}%
      </span>
    </div>

    <!-- ── Message ──────────────────────────────────────────────────────── -->
    <p class="alerte__message">{{ result.message }}</p>

    <!-- ── Détails match ────────────────────────────────────────────────── -->
    <div class="alerte__grid">
      <div class="alerte__cell">
        <span class="alerte__key">Seuil</span>
        <span class="alerte__val mono">
          {{ (result.match.threshold * 100).toFixed(0) }}%
        </span>
      </div>
      <div class="alerte__cell">
        <span class="alerte__key">Confiance</span>
        <span class="alerte__val" :class="confidenceClass">
          {{ confidenceLabel }}
        </span>
      </div>
      <div v-if="result.match.original_title" class="alerte__cell">
        <span class="alerte__key">Œuvre originale</span>
        <span class="alerte__val">{{ result.match.original_title }}</span>
      </div>
      <div class="alerte__cell">
        <span class="alerte__key">Analysé le</span>
        <span class="alerte__val mono">{{ formatDate(result.match.timestamp) }}</span>
      </div>
    </div>

    <!-- ── Preuve blockchain ─────────────────────────────────────────────── -->
    <template v-if="result.proof">
      <div class="alerte__section-title">Preuve certifiée</div>
      <div class="alerte__proof">
        <div class="alerte__proof-row">
          <span class="alerte__key">Tx blockchain</span>
          <code class="alerte__hash">{{ truncate(result.proof.tx_hash) }}</code>
        </div>
        <div class="alerte__proof-row">
          <span class="alerte__key">Hash preuve</span>
          <code class="alerte__hash">{{ truncate(result.proof.evidence_hash) }}</code>
        </div>
        <div class="alerte__proof-row">
          <span class="alerte__key">CID rapport IPFS</span>
          <code class="alerte__hash">{{ truncate(result.proof.report_cid) }}</code>
        </div>
        <div class="alerte__proof-row">
          <span class="alerte__key">CID suspect IPFS</span>
          <code class="alerte__hash">{{ truncate(result.proof.suspect_cid) }}</code>
        </div>
      </div>
    </template>

    <!-- ── DMCA Takedown ─────────────────────────────────────────────────── -->
    <template v-if="result.takedown_request">
      <div class="alerte__section-title">Notification DMCA</div>
      <div class="alerte__takedown">
        <div class="alerte__takedown-status">
          <span
            class="alerte__status-badge"
            :class="`alerte__status-badge--${result.takedown_request.status.toLowerCase()}`"
          >
            {{ result.takedown_request.status }}
          </span>
          <span class="alerte__takedown-id mono">
            ID : {{ result.takedown_request.id.slice(0, 16) }}...
          </span>
        </div>
        <p class="alerte__takedown-note">
          La preuve est certifiée on-chain et exploitable dans une
          procédure de retrait officielle (DMCA).
          CID rapport : <code>{{ result.proof?.report_cid }}</code>
        </p>
      </div>
    </template>

    <!-- ── Rapport textuel ───────────────────────────────────────────────── -->
    <template v-if="result.proof">
      <div class="alerte__section-title">Rapport forensique</div>
      <pre class="alerte__rapport">{{ generateRapport(result) }}</pre>
    </template>

  </div>
</template>

<script setup>
import { computed } from 'vue'

// ── Props ─────────────────────────────────────────────────────────────────────
const props = defineProps({
  result: {
    type:    Object,
    default: null
    // Structure : { match, proof, takedown_request, message }
  }
})

// ── Computed ──────────────────────────────────────────────────────────────────
const alerteClass = computed(() => ({
  'alerte--piracy': props.result?.match?.is_match,
  'alerte--legal':  !props.result?.match?.is_match
}))

const confidenceLabel = computed(() => {
  const s = props.result?.match?.score ?? 0
  if (s >= 0.95) return 'TRÈS HAUTE'
  if (s >= 0.85) return 'HAUTE'
  if (s >= 0.70) return 'MOYENNE'
  return 'FAIBLE'
})

const confidenceClass = computed(() => ({
  'conf--very-high': props.result?.match?.score >= 0.95,
  'conf--high':      props.result?.match?.score >= 0.85 && props.result?.match?.score < 0.95,
  'conf--medium':    props.result?.match?.score >= 0.70 && props.result?.match?.score < 0.85,
  'conf--low':       props.result?.match?.score < 0.70,
}))

// ── Helpers ───────────────────────────────────────────────────────────────────
function truncate(str, n = 20) {
  if (!str) return '—'
  return str.length > n * 2 ? `${str.slice(0, n)}...${str.slice(-8)}` : str
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR')
}

function generateRapport(r) {
  if (!r?.proof) return ''
  const p = r.proof
  const m = r.match
  return [
    '=== RAPPORT FORENSIQUE DE PIRATERIE ===',
    `Date              : ${formatDate(p.timestamp)}`,
    `ID preuve         : ${p.id}`,
    `Score similarité  : ${(m.score * 100).toFixed(4)}%`,
    `Œuvre originale   : ${m.original_hash ?? '—'}`,
    `Titre original    : ${m.original_title ?? '—'}`,
    `CID original      : ${p.original_cid}`,
    `CID suspect       : ${p.suspect_cid}`,
    `CID rapport       : ${p.report_cid}`,
    `Hash preuve       : ${p.evidence_hash ?? '—'}`,
    `Tx blockchain     : ${p.tx_hash ?? '—'}`,
    '======================================='
  ].join('\n')
}
</script>

<style scoped>
.alerte {
  border-radius: 12px;
  border:        1.5px solid;
  padding:       24px;
  display:       flex;
  flex-direction: column;
  gap:           16px;
}
.alerte--piracy {
  border-color: var(--red);
  background:   color-mix(in srgb, var(--red) 5%, var(--card));
}
.alerte--legal {
  border-color: var(--green);
  background:   color-mix(in srgb, var(--green) 5%, var(--card));
}
.alerte__header {
  display:         flex;
  justify-content: space-between;
  align-items:     center;
  flex-wrap:       wrap;
  gap:             8px;
}
.alerte__badge {
  display:     flex;
  align-items: center;
  gap:         8px;
  font-size:   1rem;
  font-weight: 700;
  color:       var(--text);
}
.alerte--piracy .alerte__badge { color: var(--red); }
.alerte--legal  .alerte__badge { color: var(--green); }

.alerte__dot {
  width:         10px;
  height:        10px;
  border-radius: 50%;
  display:       inline-block;
  animation:     pulse 1.5s infinite;
}
.alerte--piracy .alerte__dot { background: var(--red); }
.alerte--legal  .alerte__dot { background: var(--green); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
.alerte__score {
  font-family: var(--mono);
  font-size:   0.85rem;
  color:       var(--muted);
}
.alerte__message {
  font-size: 0.9rem;
  color:     var(--text);
  margin:    0;
  line-height: 1.5;
}
.alerte__grid {
  display:               grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap:                   10px;
}
.alerte__cell {
  background:    var(--surface);
  border:        1px solid var(--border);
  border-radius: 8px;
  padding:       10px 14px;
  display:       flex;
  flex-direction: column;
  gap:           4px;
}
.alerte__key {
  font-size:  0.72rem;
  color:      var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.alerte__val {
  font-size:  0.88rem;
  color:      var(--text);
  font-weight: 600;
}
.alerte__val.mono { font-family: var(--mono); }
.conf--very-high { color: var(--green); }
.conf--high      { color: #86efac; }
.conf--medium    { color: var(--yellow); }
.conf--low       { color: var(--muted); }

.alerte__section-title {
  font-size:   0.75rem;
  font-weight: 700;
  color:       var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding-bottom: 4px;
  border-bottom:  1px solid var(--border);
}
.alerte__proof {
  display:        flex;
  flex-direction: column;
  gap:            8px;
}
.alerte__proof-row {
  display:     flex;
  align-items: center;
  gap:         12px;
  flex-wrap:   wrap;
}
.alerte__proof-row .alerte__key {
  min-width: 130px;
  flex-shrink: 0;
}
.alerte__hash {
  font-family:   var(--mono);
  font-size:     0.78rem;
  color:         var(--accent);
  word-break:    break-all;
  background:    var(--surface);
  padding:       2px 8px;
  border-radius: 4px;
  border:        1px solid var(--border);
}
.alerte__takedown-status {
  display:     flex;
  align-items: center;
  gap:         12px;
}
.alerte__status-badge {
  padding:       3px 10px;
  border-radius: 99px;
  font-size:     0.75rem;
  font-weight:   700;
  font-family:   var(--mono);
}
.alerte__status-badge--sent      { background: color-mix(in srgb, var(--green) 15%, transparent); color: var(--green); }
.alerte__status-badge--simulated { background: color-mix(in srgb, var(--yellow) 15%, transparent); color: var(--yellow); }
.alerte__status-badge--pending   { background: color-mix(in srgb, var(--muted) 15%, transparent); color: var(--muted); }

.alerte__takedown-id { font-size: 0.78rem; color: var(--muted); }
.alerte__takedown-note {
  font-size:   0.82rem;
  color:       var(--muted);
  margin:      0;
  line-height: 1.5;
}
.alerte__takedown-note code {
  font-family: var(--mono);
  color:       var(--accent);
  font-size:   0.78rem;
}
.alerte__rapport {
  background:    var(--surface);
  border:        1px solid var(--border);
  border-radius: 8px;
  padding:       16px;
  font-family:   var(--mono);
  font-size:     0.75rem;
  color:         var(--text);
  white-space:   pre-wrap;
  word-break:    break-all;
  line-height:   1.7;
  margin:        0;
}
</style>