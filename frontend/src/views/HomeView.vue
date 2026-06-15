<template>
  <div class="home">

    <!-- ── Hero ───────────────────────────────────────────────────────────── -->
    <section class="hero">
      <div class="hero__label">Mémoire Licence · IA + Blockchain</div>
      <h1 class="hero__title">
        Lutte contre la<br/>
        <span class="hero__accent">Piraterie Musicale</span>
      </h1>
      <p class="hero__subtitle">
        Pipeline intégré de bout en bout : détection par intelligence artificielle
        (GraFPrint), certification de preuves on-chain (MusicRegistry) et
        simulation de distribution des redevances (Solidity + Web3.py).
      </p>
      <div class="hero__ctas">
        <router-link class="btn btn--primary" to="/detection">
          Tester la détection
        </router-link>
        <router-link class="btn btn--secondary" to="/redevances">
          Simuler les redevances
        </router-link>
      </div>
    </section>

    <!-- ── Statut des services ────────────────────────────────────────────── -->
    <section class="services">
      <div class="services__title">État du système</div>
      <div class="services__grid">
        <div
          v-for="s in servicesList"
          :key="s.label"
          class="services__card"
          :class="serviceCardClass(s)"
        >
          <span class="services__dot" :class="dotClass(s)" />
          <div>
            <div class="services__card-label">{{ s.label }}</div>
            <div class="services__card-detail">{{ s.detail }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Pipeline ───────────────────────────────────────────────────────── -->
    <section class="pipeline">
      <div class="pipeline__title">Pipeline intégré — 5 étapes</div>
      <div class="pipeline__steps">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="pipeline__step"
          :class="{ 'pipeline__step--lacune': step.lacune }"
        >
          <div class="pipeline__step-num">{{ i + 1 }}</div>
          <div>
            <div class="pipeline__step-name">{{ step.name }}</div>
            <div class="pipeline__step-desc">{{ step.desc }}</div>
          </div>
          <span v-if="step.lacune" class="pipeline__lacune-badge">
            Lacune centrale
          </span>
          <span v-else-if="step.simulated" class="pipeline__sim-badge">
            Simulé
          </span>
          <span v-else class="pipeline__ok-badge">Opérationnel</span>
        </div>
      </div>
    </section>

    <!-- ── Flux ───────────────────────────────────────────────────────────── -->
    <section class="flux">
      <router-link class="flux__card flux__card--red" to="/detection">
        <div class="flux__card-icon">⚠</div>
        <div>
          <div class="flux__card-title">Flux 1 — Détection</div>
          <div class="flux__card-desc">
            Soumettre un fichier suspect, comparer les empreintes GraFPrint,
            certifier la preuve on-chain, simuler le retrait DMCA.
          </div>
        </div>
        <div class="flux__arrow">→</div>
      </router-link>
      <router-link class="flux__card flux__card--green" to="/redevances">
        <div class="flux__card-icon">✓</div>
        <div>
          <div class="flux__card-title">Flux 2 — Redevances</div>
          <div class="flux__card-desc">
            Sélectionner une œuvre enregistrée, simuler la distribution
            des revenus via <code>simulateRoyaltyPayment()</code> on-chain.
          </div>
        </div>
        <div class="flux__arrow">→</div>
      </router-link>
    </section>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchHealth }    from '@/services/api.js'

// ── State ─────────────────────────────────────────────────────────────────────
const health = ref(null)

const servicesList = ref([
  { label: 'API Backend',    detail: 'FastAPI — port 8000',   key: null,          status: 'checking' },
  { label: 'Modèle GraFPrint', detail: 'GNN fingerprinting', key: 'model_loaded', status: 'checking' },
  { label: 'IPFS',           detail: 'Stockage décentralisé', key: 'ipfs',         status: 'checking' },
  { label: 'Blockchain',     detail: 'Ganache / Polygon',     key: 'blockchain',   status: 'checking' },
  { label: 'Œuvres indexées', detail: 'Base d\'empreintes',  key: 'works_indexed', status: 'info' },
])

const steps = [
  { name: 'Enregistrement',      desc: 'GraFPrint → IPFS → MusicRegistry',          lacune: false, simulated: false },
  { name: 'Surveillance',        desc: 'Comparaison d\'empreintes en temps réel',    lacune: false, simulated: false },
  { name: 'Certification',       desc: 'Preuve IPFS + ancrage blockchain',           lacune: false, simulated: false },
  { name: 'Enforcement externe', desc: 'Déclenchement DMCA sur plateformes tierces', lacune: true,  simulated: false },
  { name: 'Distribution',        desc: 'simulateRoyaltyPayment() + PaymentSimulated', lacune: false, simulated: true  },
]

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    health.value = await fetchHealth()
    // Mise à jour statuts api
    servicesList.value[0].status = 'ok'
    servicesList.value.forEach(s => {
      if (!s.key) return
      if (s.key === 'works_indexed') {
        s.detail = `${health.value.works_indexed} empreinte(s) indexée(s)`
        s.status = 'info'
      } else {
        s.status = health.value[s.key] ? 'ok' : 'error'
      }
    })
  } catch {
    servicesList.value[0].status = 'error'
    servicesList.value.forEach(s => {
      if (s.status === 'checking') s.status = 'unknown'
    })
  }
})

// ── Helpers ───────────────────────────────────────────────────────────────────
function serviceCardClass(s) {
  return {
    'services__card--ok':      s.status === 'ok',
    'services__card--error':   s.status === 'error',
    'services__card--info':    s.status === 'info',
    'services__card--unknown': s.status === 'checking' || s.status === 'unknown',
  }
}
function dotClass(s) {
  return {
    'services__dot--ok':      s.status === 'ok',
    'services__dot--error':   s.status === 'error',
    'services__dot--info':    s.status === 'info',
    'services__dot--unknown': s.status === 'checking' || s.status === 'unknown',
  }
}
</script>

<style scoped>
.home { display: flex; flex-direction: column; gap: 48px; }

/* Hero */
.hero { text-align: center; padding: 48px 0 24px; }
.hero__label {
  display:       inline-block;
  font-size:     0.75rem;
  font-family:   var(--mono);
  color:         var(--accent);
  background:    color-mix(in srgb, var(--accent) 10%, transparent);
  border:        1px solid color-mix(in srgb, var(--accent) 25%, transparent);
  padding:       4px 14px;
  border-radius: 99px;
  margin-bottom: 16px;
}
.hero__title {
  font-size:   2.8rem;
  font-weight: 800;
  color:       var(--text);
  line-height: 1.15;
  margin:      0 0 16px;
}
.hero__accent { color: var(--accent); }
.hero__subtitle {
  font-size:  1rem;
  color:      var(--muted);
  max-width:  600px;
  margin:     0 auto 32px;
  line-height: 1.7;
}
.hero__ctas { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.btn {
  padding:       12px 28px;
  border-radius: 8px;
  font-size:     0.92rem;
  font-weight:   700;
  font-family:   inherit;
  text-decoration: none;
  transition:    all 0.2s;
  cursor:        pointer;
  border:        none;
}
.btn--primary  { background: var(--accent); color: #fff; }
.btn--secondary { background: transparent; border: 1.5px solid var(--border); color: var(--text); }
.btn--primary:hover  { opacity: 0.85; }
.btn--secondary:hover { border-color: var(--accent); color: var(--accent); }

/* Services */
.services__title,
.pipeline__title { font-size: 0.75rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px; }
.services__grid {
  display:               grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap:                   10px;
}
.services__card {
  background:    var(--card);
  border:        1px solid var(--border);
  border-radius: 10px;
  padding:       14px 16px;
  display:       flex;
  align-items:   center;
  gap:           12px;
  transition:    border-color 0.2s;
}
.services__card--ok    { border-color: color-mix(in srgb, var(--green) 30%, var(--border)); }
.services__card--error { border-color: color-mix(in srgb, var(--red) 30%, var(--border)); }
.services__dot {
  width:         10px;
  height:        10px;
  border-radius: 50%;
  flex-shrink:   0;
}
.services__dot--ok      { background: var(--green); }
.services__dot--error   { background: var(--red); }
.services__dot--info    { background: var(--accent); }
.services__dot--unknown { background: var(--muted); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.services__card-label  { font-size: 0.88rem; font-weight: 600; color: var(--text); }
.services__card-detail { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }

/* Pipeline */
.pipeline__steps { display: flex; flex-direction: column; gap: 8px; }
.pipeline__step {
  background:    var(--card);
  border:        1px solid var(--border);
  border-radius: 10px;
  padding:       14px 18px;
  display:       flex;
  align-items:   center;
  gap:           16px;
}
.pipeline__step--lacune {
  border-color: color-mix(in srgb, var(--yellow) 35%, var(--border));
  background:   color-mix(in srgb, var(--yellow) 4%, var(--card));
}
.pipeline__step-num {
  width:           30px;
  height:          30px;
  border-radius:   50%;
  background:      var(--accent);
  color:           #fff;
  display:         flex;
  align-items:     center;
  justify-content: center;
  font-size:       0.82rem;
  font-weight:     700;
  flex-shrink:     0;
}
.pipeline__step--lacune .pipeline__step-num { background: var(--yellow); color: #000; }
.pipeline__step-name { font-size: 0.9rem; font-weight: 600; color: var(--text); }
.pipeline__step-desc { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
.pipeline__step .pipeline__ok-badge,
.pipeline__step .pipeline__sim-badge,
.pipeline__step .pipeline__lacune-badge {
  margin-left:   auto;
  padding:       3px 10px;
  border-radius: 99px;
  font-size:     0.72rem;
  font-weight:   700;
  font-family:   var(--mono);
  flex-shrink:   0;
}
.pipeline__ok-badge     { background: color-mix(in srgb, var(--green) 12%, transparent); color: var(--green); }
.pipeline__sim-badge    { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); }
.pipeline__lacune-badge { background: color-mix(in srgb, var(--yellow) 12%, transparent); color: var(--yellow); }

/* Flux */
.flux { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 700px) { .flux { grid-template-columns: 1fr; } }
.flux__card {
  border:          1.5px solid;
  border-radius:   12px;
  padding:         24px;
  display:         flex;
  align-items:     flex-start;
  gap:             16px;
  text-decoration: none;
  transition:      all 0.2s;
  cursor:          pointer;
}
.flux__card--red   { border-color: color-mix(in srgb, var(--red) 30%, var(--border)); background: color-mix(in srgb, var(--red) 4%, var(--card)); }
.flux__card--green { border-color: color-mix(in srgb, var(--green) 30%, var(--border)); background: color-mix(in srgb, var(--green) 4%, var(--card)); }
.flux__card:hover  { transform: translateY(-2px); }
.flux__card-icon   { font-size: 1.6rem; flex-shrink: 0; }
.flux__card--red   .flux__card-icon { color: var(--red); }
.flux__card--green .flux__card-icon { color: var(--green); }
.flux__card-title  { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.flux__card-desc   { font-size: 0.82rem; color: var(--muted); line-height: 1.5; }
.flux__card-desc code { font-family: var(--mono); color: var(--accent); font-size: 0.78rem; }
.flux__arrow { margin-left: auto; font-size: 1.2rem; color: var(--muted); flex-shrink: 0; align-self: center; }
</style>