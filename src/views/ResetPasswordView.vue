<template>
  <div class="reset-page">
    <div class="card">
      <!-- Estado de verificación -->
      <div v-if="verifying" class="card-header">
        <span class="icon">🔍</span>
        <h1>Verificando enlace</h1>
        <p>Por favor espera un momento...</p>
        <div class="spinner-container">
          <div class="spinner"></div>
        </div>
      </div>

      <!-- Estado de redirección con spinner -->
      <div v-else-if="redirecting" class="card-header">
        <span class="icon">⚠️</span>
        <h1>{{ redirectTitle }}</h1>
        <p>{{ redirectText }}</p>
        <div class="spinner-container">
          <div class="spinner"></div>
        </div>
      </div>

      <!-- Formulario solo si el token es válido -->
      <template v-else-if="isValidToken">
        <div class="card-header">
          <span class="icon">🔒</span>
          <h1>Nueva contraseña</h1>
          <p>Escribe tu nueva contraseña</p>
        </div>

        <input
          v-model="password"
          type="password"
          placeholder="Nueva contraseña (mínimo 6 caracteres)"
          @input="clearMessages"
        />

        <button @click="handleUpdate" :disabled="loading || !password || password.length < 6">
          <span v-if="!loading">Actualizar contraseña</span>
          <div v-else class="button-spinner"></div>
        </button>

        <p v-if="msg" class="success">{{ msg }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </template>

      <!-- Token inválido o expirado -->
      <div v-else-if="!verifying && !isValidToken && !redirecting" class="error-container">
        <div class="card-header">
          <span class="error-icon">⚠️</span>
          <h1 class="error-title">Enlace inválido</h1>
          <p class="error-subtitle">Redirigiendo al inicio...</p>
        </div>
        
        <div class="error-message-box">
          <p>Este enlace ya fue usado o ha caducado.</p>
          <p>Serás redirigido automáticamente.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '@/lib/supabaseClient'
import { useRouter } from 'vue-router'

const router = useRouter()
const password = ref('')
const loading = ref(false)
const redirecting = ref(false)
const redirectTitle = ref('')
const redirectText = ref('')
const msg = ref('')
const error = ref('')
const verifying = ref(true)
const isValidToken = ref(false)

function clearMessages() {
  msg.value = ''
  error.value = ''
}

// spinner
function redirectToHome(title, text) {
  redirectTitle.value = title
  redirectText.value = text
  redirecting.value = true

  setTimeout(() => {
    window.location.href = '/' 
  }, 2000)
}

async function verifyToken() {
  verifying.value = true
  
  const { data: { session }, error: sessionError } = await supabase.auth.getSession()
  
  if (session && !sessionError) {
    isValidToken.value = true
    verifying.value = false
    window.history.replaceState({}, document.title, '/reset-password')
    return
  }
  
  isValidToken.value = false
  verifying.value = false
  
  redirectToHome('Enlace inválido', 'Redirigiendo al inicio...')
}

async function handleUpdate() {
  if (!password.value) {
    error.value = 'Ingresa una contraseña'
    return
  }

  if (password.value.length < 6) {
    error.value = 'La contraseña debe tener al menos 6 caracteres'
    return
  }

  loading.value = true
  msg.value = ''
  error.value = ''

  try {
    const { error: updateError } = await supabase.auth.updateUser({ 
      password: password.value 
    })

    if (updateError) {
      loading.value = false
      
      if (updateError.message.includes('expired') || updateError.status === 403) {
        redirectToHome('Enlace expirado', 'Redirigiendo al inicio...')
      } else {
        error.value = updateError.message
      }
      return
    }

    loading.value = false
    await supabase.auth.signOut()
    redirectToHome('¡Contraseña actualizada!', 'Redirigiendo al inicio...')
    
  } catch (e) {
    loading.value = false
    error.value = 'Ocurrió un error. Intenta de nuevo.'
  }
}

onMounted(() => {
  verifyToken()
})
</script>

<style scoped>
.reset-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-size: 400% 400%;
  animation: bgMove 15s ease infinite;
}

@keyframes bgMove {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.card {
  background: rgba(18,18,18,0.95);
  backdrop-filter: blur(10px);
  padding: 2rem;
  border-radius: 16px;
  color: white;
  width: 350px;
  text-align: center;
  border: 1px solid rgba(110,180,232,0.2);
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px);}
  to { opacity: 1; transform: translateY(0);}
}

.card-header {
  margin-bottom: 1.5rem;
}

.card-header h1 {
  font-size: 1.5rem;
  background: linear-gradient(135deg, #e8e4dc, #6eb4e8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0.3rem 0 0.5rem 0;
}

.card-header p {
  color: #6b6560;
  font-size: 0.9rem;
}

.icon {
  font-size: 2rem;
  color: #6eb4e8;
  display: block;
  margin-bottom: 0.5rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,100% { transform: scale(1);}
  50% { transform: scale(1.1);}
}

input {
  width: 100%;
  padding: 0.7rem;
  margin-bottom: 1rem;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.05);
  color: #fff;
  font-size: 1rem;
  transition: all 0.3s ease;
}

input:focus {
  outline: none;
  border-color: #6eb4e8;
  background: rgba(255,255,255,0.1);
}

button {
  width: 100%;
  padding: 0.7rem;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #6eb4e8, #4a90c4);
  font-weight: bold;
  cursor: pointer;
  color: white;
  font-size: 1rem;
  transition: transform 0.2s ease;
  display: flex;
  justify-content: center;
  align-items: center;
}

button:hover:not(:disabled) {
  transform: translateY(-2px);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.success {
  color: #6fcf97;
  margin-top: 1rem;
  padding: 0.5rem;
  background: rgba(111, 207, 151, 0.1);
  border-radius: 8px;
  animation: slideDown 0.3s ease;
}

.error {
  color: #e07070;
  margin-top: 1rem;
  padding: 0.5rem;
  background: rgba(224, 112, 112, 0.1);
  border-radius: 8px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.error-container {
  text-align: center;
}

.error-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 0.5rem;
}

.error-title {
  font-size: 1.5rem !important;
  background: linear-gradient(135deg, #e07070, #c04e4e) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  margin-bottom: 0.5rem !important;
}

.error-subtitle {
  color: #6b6560;
  font-size: 0.9rem;
}

.error-message-box {
  background: rgba(224, 112, 112, 0.1);
  padding: 1rem;
  border-radius: 8px;
  margin: 1.5rem 0;
  border: 1px solid rgba(224, 112, 112, 0.2);
}

.error-message-box p {
  color: #e07070;
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.spinner-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1.5rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(110, 180, 232, 0.2);
  border-top-color: #6eb4e8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.button-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>