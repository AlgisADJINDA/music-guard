<template>
  <div class="redev">

    <div class="page-header">
      <router-link class="page-back" to="/">← Accueil</router-link>
      <h1 class="page-title">
        <span class="page-title__badge page-title__badge--green">Flux 2</span>
        Simulation des Redevances
      </h1>
      <p class="page-desc">
        Déclenchez <code>simulateRoyaltyPayment()</code> dans le smart contract
        <code>MusicRegistry</code>. Pour chaque ayant droit, un événement
        <code>PaymentSimulated</code> est émis on-chain.
        Aucun transfert réel n'est effectué.
      </p>
    </div>

    <!-- ── Aide hash ──────────────────────────────────────────────────────── -->
    <div v-if="!prefillHash" class="hint-box">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8"  x2="12"   y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p>
        Le hash de l'œuvre est généré lors de l'enregistrement (Flux 1).
        <router-link to="/detection">Enregistrez d'abord une œuvre</router-link>
        pour obtenir un hash valide.
      </p>
    </div>

    <!-- ── Formulaire ─────────────────────────────────────────────────────── -->
    <div class="panel">
      <div class="panel__header">
        <div class="panel__title">Paramètres de simulation</div>
      </div>
      <div class="panel__body">
        <SimulationRedevances :prefill-hash="prefillHash" />
      </div>
    </div>

    <!-- ── Explication académique ────────────────────────────────────────── -->
    <div class="academic">
      <div class="academic__title">Contexte scientifique</div>
      <div class="academic__grid">
        <div class="academic__card">
          <div class="academic__card-title">Principe</div>
          <p>
            La distribution automatisée des redevances via smart contracts
            résout le problème de la « boîte noire » des sociétés de gestion
            collective, où des fonds restaient non distribués.
          </p>
        </div>
        <div class="academic__card">
          <div class="academic__card-title">Référence littérature</div>
          <p>
            Ciriello et al. (2023) formalisent les principes :
            registre distribué, mécanisme de consensus, et
            paiements automatiques via smart contracts avec stablecoins.
            Pan et al. (2024) valident l'équité par modélisation par agents.
          </p>
        </div>
        <div class="academic__card">
          <div class="academic__card-title">Implémentation</div>
          <p>
            La fonction <code>simulateRoyaltyPayment(workHash, totalAmount)</code>
            itère sur les bénéficiaires enregistrés et calcule
            <code>montant = (totalAmount × share) / 100</code>
            pour chaque adresse Ethereum.
          </p>
        </div>
        <div class="academic__card">
          <div class="academic__card-title">Limite du prototype</div>
          <p>
            Les événements <code>PaymentSimulated</code> sont émis on-chain
            sans transfert réel de valeur. Un déploiement en production
            sur Polygon intégrerait des stablecoins (USDC) pour les
            virements effectifs.
          </p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted }  from 'vue'
import { useRoute }        from 'vue-router'
import SimulationRedevances from '@/components/SimulationRedevances.vue'

const route       = useRoute()
const prefillHash = ref(route.query.hash || '')
</script>

<style scoped>
.redev { display: flex; flex-direction: column; gap: 28px; }

.page-header { display: flex; flex-direction: column; gap: 8px; }
.page-back   { font-size: 0.82rem; color: var(--muted); text-decoration: none; }
.page-back:hover { color: var(--accent); }
.page-title  {
  font-size: 1.8rem; font-weight: 800; color: var(--text);
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.page-title__badge {
  font-size: 0.72rem; padding: 4px 10px; border-radius: 99px;
  font-family: var(--mono); font-weight: 700;
}
.page-title__badge--green {
  background: color-mix(in srgb, var(--green) 15%, transparent);
  color: var(--green);
}
.page-desc { font-size: 0.88rem; color: var(--muted); line-height: 1.6; }
.page-desc code { font-family: var(--mono); color: var(--accent); }

.hint-box {
  display:       flex;
  gap:           12px;
  align-items:   flex-start;
  background:    color-mix(in srgb, var(--accent) 5%, var(--card));
  border:        1px solid var(--border);
  border-radius: 10px;
  padding:       16px;
}
.hint-box svg { width: 18px; height: 18px; color: var(--accent); flex-shrink: 0; margin-top: 1px; }
.hint-box p   { font-size: 0.85rem; color: var(--muted); margin: 0; line-height: 1.5; }
.hint-box a   { color: var(--accent); }

.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.panel__header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
.panel__title { font-size: 1rem; font-weight: 700; color: var(--text); }
.panel__body  { padding: 24px; }

.academic {
  background:    var(--card);
  border:        1px solid var(--border);
  border-radius: 12px;
  padding:       24px;
}
.academic__title {
  font-size:   0.75rem;
  font-weight: 700;
  color:       var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.academic__grid {
  display:               grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap:                   14px;
}
.academic__card {
  background:    var(--surface);
  border:        1px solid var(--border);
  border-radius: 8px;
  padding:       16px;
  display:       flex;
  flex-direction: column;
  gap:           8px;
}
.academic__card-title {
  font-size:   0.78rem;
  font-weight: 700;
  color:       var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.academic__card p {
  font-size:   0.82rem;
  color:       var(--muted);
  margin:      0;
  line-height: 1.6;
}
.academic__card code { font-family: var(--mono); color: var(--accent); font-size: 0.78rem; }
</style>