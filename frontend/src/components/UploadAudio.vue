<template>
  <div
    class="upload-zone"
    :class="{
      'upload-zone--dragging': isDragging,
      'upload-zone--error':    hasError,
      'upload-zone--success':  file !== null
    }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
    @click="triggerInput"
  >
    <input
      ref="inputRef"
      type="file"
      :accept="accept"
      class="upload-input"
      @change="onFileChange"
    />

    <!-- Icône -->
    <div class="upload-icon">
      <svg v-if="!file" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M9 12l2 2 4-4"/>
        <circle cx="12" cy="12" r="10"/>
      </svg>
    </div>

    <!-- Texte principal -->
    <p class="upload-label">
      <template v-if="!file">
        {{ label || 'Déposer un fichier audio ici' }}
      </template>
      <template v-else>
        {{ file.name }}
      </template>
    </p>

    <!-- Sous-texte -->
    <p class="upload-sublabel">
      <template v-if="!file">
        WAV ou MP3 — cliquez ou glissez-déposez
      </template>
      <template v-else>
        {{ formatSize(file.size) }} —
        <button class="upload-clear" @click.stop="clearFile">
          supprimer
        </button>
      </template>
    </p>

    <!-- Barre de progression -->
    <div v-if="progress > 0 && progress < 100" class="upload-progress">
      <div
        class="upload-progress-bar"
        :style="{ width: progress + '%' }"
      />
      <span class="upload-progress-label">{{ progress }}%</span>
    </div>

    <!-- Erreur -->
    <p v-if="hasError" class="upload-error">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// ── Props ─────────────────────────────────────────────────────────────────────
const props = defineProps({
  label:    { type: String,  default: '' },
  accept:   { type: String,  default: 'audio/wav,audio/mpeg,.wav,.mp3' },
  progress: { type: Number,  default: 0 },
  maxMb:    { type: Number,  default: 50 }
})

// ── Emits ─────────────────────────────────────────────────────────────────────
const emit = defineEmits(['file-selected', 'file-cleared'])

// ── State ─────────────────────────────────────────────────────────────────────
const inputRef  = ref(null)
const file      = ref(null)
const isDragging = ref(false)
const errorMsg  = ref('')

const hasError = computed(() => errorMsg.value !== '')

// ── Méthodes ──────────────────────────────────────────────────────────────────
function triggerInput() {
  inputRef.value?.click()
}

function validateFile(f) {
  const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-wav']
  const validExts  = ['.wav', '.mp3']
  const name       = f.name.toLowerCase()
  const isValidType = validTypes.includes(f.type) ||
                      validExts.some(ext => name.endsWith(ext))

  if (!isValidType) {
    return 'Format non supporté. Utiliser WAV ou MP3.'
  }
  if (f.size > props.maxMb * 1024 * 1024) {
    return `Fichier trop volumineux (max ${props.maxMb} Mo).`
  }
  if (f.size === 0) {
    return 'Fichier vide.'
  }
  return ''
}

function selectFile(f) {
  const err = validateFile(f)
  if (err) {
    errorMsg.value = err
    file.value     = null
    return
  }
  errorMsg.value = ''
  file.value     = f
  emit('file-selected', f)
}

function onFileChange(e) {
  if (e.target.files[0]) selectFile(e.target.files[0])
}

function onDrop(e) {
  isDragging.value = false
  const dropped    = e.dataTransfer?.files[0]
  if (dropped) selectFile(dropped)
}

function clearFile() {
  file.value         = null
  errorMsg.value     = ''
  if (inputRef.value) inputRef.value.value = ''
  emit('file-cleared')
}

function formatSize(bytes) {
  if (bytes < 1024)       return `${bytes} o`
  if (bytes < 1024 ** 2)  return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / 1024 ** 2).toFixed(1)} Mo`
}
</script>

<style scoped>
.upload-zone {
  position:        relative;
  display:         flex;
  flex-direction:  column;
  align-items:     center;
  justify-content: center;
  gap:             10px;
  padding:         32px 24px;
  border:          1.5px dashed var(--border);
  border-radius:   12px;
  background:      var(--surface);
  cursor:          pointer;
  transition:      all 0.2s ease;
  min-height:      140px;
  text-align:      center;
}
.upload-zone:hover,
.upload-zone--dragging {
  border-color:    var(--accent);
  background:      color-mix(in srgb, var(--accent) 6%, var(--surface));
}
.upload-zone--success {
  border-color:  var(--green);
  border-style:  solid;
}
.upload-zone--error {
  border-color:  var(--red);
  border-style:  solid;
}
.upload-input {
  display: none;
}
.upload-icon svg {
  width:  36px;
  height: 36px;
  color:  var(--accent);
}
.upload-zone--success .upload-icon svg {
  color: var(--green);
}
.upload-label {
  font-size:   0.95rem;
  font-weight: 600;
  color:       var(--text);
  margin:      0;
  word-break:  break-all;
}
.upload-sublabel {
  font-size: 0.8rem;
  color:     var(--muted);
  margin:    0;
}
.upload-clear {
  background:  none;
  border:      none;
  color:       var(--red);
  cursor:      pointer;
  padding:     0;
  font-size:   0.8rem;
  text-decoration: underline;
}
.upload-progress {
  width:    100%;
  position: relative;
  height:   6px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
  margin-top: 8px;
}
.upload-progress-bar {
  height:     100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.3s ease;
}
.upload-progress-label {
  position:   absolute;
  right:      0;
  top:        -18px;
  font-size:  0.72rem;
  color:      var(--muted);
  font-family: var(--mono);
}
.upload-error {
  color:     var(--red);
  font-size: 0.8rem;
  margin:    0;
}
</style>