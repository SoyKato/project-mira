<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <RouterLink to="/" class="brand-link">
          <img 
            :src="flame"
            alt="logo"
            class="brand-icon"
          />
          <span class="brand-text">MIRA</span>
        </RouterLink>
      </div>

      <div class="nav-links">
        <RouterLink to="/" class="nav-link">Inicio</RouterLink>

        <template v-if="!isAuthenticated">
          <RouterLink to="/login" class="nav-link nav-link--cta">
            Iniciar sesión
          </RouterLink>
          <RouterLink to="/register" class="nav-link nav-link--cta">
            Registrarse
          </RouterLink>
        </template>

        
        <template v-else>
          <RouterLink to="/dashboard" class="nav-link">Dashboard</RouterLink>
       <!-- <span class="nav-user">{{ user?.name }}</span> -->
          <button class="nav-link nav-link--logout" @click="handleLogout">
            Cerrar sesión
          </button>
        </template>
      </div>
    </nav>

    <main class="main-content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

import flame from '/src/logo.png'

const router = useRouter()
const { isAuthenticated, user, logout } = useAuth()

async function handleLogout() {
  logout()
  await router.push('/login')
}
</script>

<style>

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: linear-gradient(90deg, #000, #021026, #22013e, #000);
  background-size: 300% 300%;
  animation: glitch 15s infinite;
}

@keyframes glitch {
  0% { background-position: 0% 50%; }
  20% { background-position: 100% 30%; }
  40% { background-position: 20% 70%; }
  60% { background-position: 80% 20%; }
  80% { background-position: 10% 90%; }
  100% { background-position: 0% 50%; }
}
</style>

<style scoped>
#app {
  min-height: 100vh;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2.5rem;
  background: rgb(255, 255, 255);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  font-weight: 700;
  font-size: 1.2rem;
  letter-spacing: -0.02em;
}

.brand-icon {
  width: 50px;           
  height: 50px;
  object-fit: contain;
  border-radius: 10%;
  display: block;
}

.brand-text {
  background: linear-gradient(135deg, #aa00ff, #000000);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: 2rem;
  font-weight: 700;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-link {
  padding: 0.45rem 1rem;
  border-radius: 8px;
  color: #000000;
  background: #ffffff;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.25s ease;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
}

.nav-link:hover,
.nav-link--cta:hover {
  background: linear-gradient(135deg, #000000);
  color: #ffffff;
  padding: 0.45rem 1.25rem;
  font-weight: 600;
}

.nav-link.router-link-active {
  color: #ffffff;
  font-weight: 600;
  background: linear-gradient(135deg, #a600ff, #b300ff);
}

.nav-link--cta {
  background: linear-gradient(135deg, #ffffff, #ffffff);
  color: #000000;
  font-weight: 600;
}

.main-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.page-enter-active,
.page-leave-active {
  transition: all 0.25s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>