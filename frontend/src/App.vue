<template>
  <div class="app">

    <!-- ── Navigation ────────────────────────────────────────────────────── -->
    <nav class="nav">
      <div class="nav__inner">
        <router-link class="nav__brand" to="/">
          <span class="nav__brand-icon">♫</span>
          <span class="nav__brand-name">MusicGuard</span>
          <span class="nav__brand-tag">IA + Blockchain</span>
        </router-link>

        <div class="nav__links">
          <router-link class="nav__link" to="/">Accueil</router-link>
          <router-link class="nav__link nav__link--red" to="/detection">
            Détection
          </router-link>
          <router-link class="nav__link nav__link--green" to="/redevances">
            Redevances
          </router-link>
        </div>

        <!-- Indicateur système -->
        <div class="nav__status" :class="statusClass">
          <span class="nav__status-dot" />
          {{ statusLabel }}
        </div>
      </div>
    </nav>

    <!-- ── Contenu principal ─────────────────────────────────────────────── -->
    <main class="main">
      <div class="container">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </div>
    </main>

    <!-- ── Footer ────────────────────────────────────────────────────────── -->
    <footer class="footer">
      <div class="container">
        <span>
          ADJINDA Adékin Olatobi Algis — Mémoire Licence | Pr. Eugène EZIN
        </span>
        <span class="footer__stack">
          GraFPrint · Solidity · IPFS · Web3.py · FastAPI · Vue.js
        </span>
      </div>
    </footer>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchHealth }              from '@/services/api.js'

const health    = ref(null)
const apiOnline = ref(false)

onMounted(async () => {
  try {
    health.value    = await fetchHealth()
    apiOnline.value = true
  } catch {
    apiOnline.value = false
  }
})

const statusLabel = computed(() => {
  if (!apiOnline.value)  return 'Backend hors ligne'
  if (!health.value)     return 'Vérification...'
  const { ipfs, blockchain, model_loaded } = health.value
  if (ipfs && blockchain && model_loaded) return 'Tous les services actifs'
  if (ipfs || blockchain)                 return 'Services partiels'
  return 'Services indisponibles'
})

const statusClass = computed(() => ({
  'nav__status--ok':      apiOnline.value && health.value?.ipfs && health.value?.blockchain,
  'nav__status--warn':    apiOnline.value && !(health.value?.ipfs && health.value?.blockchain),
  'nav__status--offline': !apiOnline.value,
}))
</script>

<style>
/* ── Variables globales ──────────────────────────────────────────────────── */
:root {
  --bg:      #080b12;
  --surface: #0d1120;
  --card:    #111827;
  --border:  #1e2740;
  --accent:  #4f7cff;
  --green:   #00e5a0;
  --red:     #ff6b6b;
  --yellow:  #fbbf24;
  --text:    #e2e8f0;
  --muted:   #64748b;
  --mono:    'JetBrains Mono', monospace;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background:  var(--bg);
  color:       var(--text);
  font-family: 'Syne', sans-serif;
  min-height:  100vh;
  line-height: 1.5;
}

/* ── Layout ──────────────────────────────────────────────────────────────── */
.app { display: flex; flex-direction: column; min-height: 100vh; }

.nav {
  position:     sticky;
  top:          0;
  z-index:      100;
  background:   color-mix(in srgb, var(--bg) 85%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
.nav__inner {
  max-width:   1100px;
  margin:      0 auto;
  padding:     0 24px;
  height:      56px;
  display:     flex;
  align-items: center;
  gap:         24px;
}
.nav__brand {
  display:         flex;
  align-items:     center;
  gap:             8px;
  text-decoration: none;
  flex-shrink:     0;
}
.nav__brand-icon { font-size: 1.2rem; color: var(--accent); }
.nav__brand-name { font-size: 1rem; font-weight: 800; color: var(--text); }
.nav__brand-tag  {
  font-size:     0.68rem;
  font-family:   var(--mono);
  color:         var(--muted);
  background:    var(--surface);
  border:        1px solid var(--border);
  padding:       1px 6px;
  border-radius: 4px;
}
.nav__links {
  display:     flex;
  align-items: center;
  gap:         4px;
  flex:        1;
}
.nav__link {
  padding:         8px 14px;
  border-radius:   7px;
  text-decoration: none;
  font-size:       0.85rem;
  font-weight:     600;
  color:           var(--muted);
  transition:      all 0.15s;
}
.nav__link:hover          { color: var(--text); background: var(--surface); }
.nav__link.router-link-active { color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, var(--surface)); }
.nav__link--red.router-link-active  { color: var(--red); background: color-mix(in srgb, var(--red) 8%, var(--surface)); }
.nav__link--green.router-link-active { color: var(--green); background: color-mix(in srgb, var(--green) 8%, var(--surface)); }

.nav__status {
  display:     flex;
  align-items: center;
  gap:         6px;
  font-size:   0.72rem;
  font-family: var(--mono);
  color:       var(--muted);
  flex-shrink: 0;
  margin-left: auto;
}
.nav__status-dot {
  width:         7px;
  height:        7px;
  border-radius: 50%;
  background:    var(--muted);
}
.nav__status--ok .nav__status-dot      { background: var(--green); }
.nav__status--warn .nav__status-dot    { background: var(--yellow); }
.nav__status--offline .nav__status-dot { background: var(--red); }

.main { flex: 1; padding: 40px 0; }
.container { max-width: 900px; margin: 0 auto; padding: 0 24px; }

.footer {
  border-top: 1px solid var(--border);
  padding:    16px 0;
}
.footer .container {
  display:         flex;
  justify-content: space-between;
  align-items:     center;
  flex-wrap:       wrap;
  gap:             8px;
  font-size:       0.75rem;
  color:           var(--muted);
  font-family:     var(--mono);
}
.footer__stack { color: var(--accent); }

/* ── Transitions ─────────────────────────────────────────────────────────── */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to     { opacity: 0; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>