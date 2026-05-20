<template>
  <div class="forgot-page">

    <div class="bg-grid"></div>
    <div class="bg-glow"></div>

    <div class="card">

      <div class="card-header">
        <span class="icon">✉</span>
        <h1>Recuperar contraseña</h1>
        <p>Ingresa tu correo y te enviaremos un enlace</p>
      </div>

      <form @submit.prevent="handleReset" class="form" v-if="!emailSent">

        <div class="input-group">
          <span class="input-icon"></span>
          <input
            v-model="email"
            type="email"
            placeholder="correo@ejemplo.com"
            required
          />
        </div>

        <button :disabled="loading" class="btn">
          <span v-if="!loading">Enviar enlace</span>
          <span v-else class="spinner"></span>
        </button>

      </form>

      <Transition name="fade">
        <p v-if="msg" class="success">{{ msg }}</p>
      </Transition>

      <Transition name="fade">
        <p v-if="error" class="error">{{ error }}</p>
      </Transition>

      <!--  Botón Cancelar - se oculta cuando emailSent es true -->
      <RouterLink v-if="!emailSent && !loading" to="/" class="back-link">
        Cancelar
      </RouterLink>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '@/lib/supabaseClient'

const router = useRouter()
const email = ref('')
const loading = ref(false)
const msg = ref('')
const error = ref('')
const emailSent = ref(false) //  estado para controlar si ya se envió el email

async function handleReset() {
  loading.value = true
  msg.value = ''
  error.value = ''

  // Enviamos el link de restablecimiento de contraseña a Supabase
  const { error: err } = await supabase.auth.resetPasswordForEmail(email.value, {
    redirectTo: `${window.location.origin}/reset-password`
  })

  if (err) {
    error.value = err.message
    loading.value = false
  } else {
    emailSent.value = true //  Marcar que el email fue enviado
    msg.value = 'Revisa tu correo. Te enviamos un enlace para restablecer tu contraseña.'
    
    // Esperar 2 segundos para que el usuario vea el mensaje, luego redirigir al home
    setTimeout(() => {
      router.push('/')
    }, 2000)
  }

  loading.value = false
}
</script>

<style scoped>

.forgot-page {
  min-height: calc(100vh - 65px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}


.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(200,169,110,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(200,169,110,0.05) 1px, transparent 1px);
  background-size: 50px 50px;
}

.bg-glow {
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(110,180,232,0.12), transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}


.card {
  position: relative;
  width: 100%;
  max-width: 400px;
  background: rgba(22,22,26,0.95);
  border: 1px solid rgba(110,180,232,0.2);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px);}
  to { opacity: 1; transform: translateY(0);}
}

.card-header h1 {
  font-size: 1.5rem;
  background: linear-gradient(135deg, #e8e4dc, #6eb4e8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.card-header p {
  color: #6b6560;
  font-size: 0.9rem;
}

.icon {
  font-size: 1.8rem;
  color: #6eb4e8;
  display: block;
  margin-bottom: 0.5rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,100% { transform: scale(1);}
  50% { transform: scale(1.1);}
}


.input-group {
  position: relative;
  margin: 1.5rem 0;
}

.input-group input {
  width: 100%;
  padding: 0.7rem 2.5rem;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.05);
  color: #fff;
}

.input-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
}


.btn {
  width: 100%;
  padding: 0.75rem;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #6eb4e8, #4a90c4);
  font-weight: bold;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
}


.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(0,0,0,0.2);
  border-top-color: black;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg);}
}


.success {
  color: #6fcf97;
  margin-top: 1rem;
}

.error {
  color: #e07070;
  margin-top: 1rem;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.back-link {
  display: block;
  margin-top: 1.5rem;
  color: #6eb4e8;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

</style>