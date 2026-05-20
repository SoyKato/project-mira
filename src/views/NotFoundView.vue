<!-- src/views/NotFoundView.vue -->
<template>
  <div class="notfound">

    <!-- Fondo -->
    <div class="bg" aria-hidden="true">
      <div class="bg-orb"></div>
      <div class="bg-grid"></div>
    </div>

    <!-- Número 404 gigante de fondo -->
    <span class="ghost-number" aria-hidden="true">404</span>

    <!-- Contenido -->
    <div class="content">
      <div class="icon-wrap">
        <span class="icon">⬡</span>
      </div>

      <h1 class="title">Página no encontrada</h1>

      <p class="desc">
        La ruta <code class="route-badge">{{ currentPath }}</code> no existe
        en esta aplicación.
      </p>

      <div class="actions">
        <RouterLink to="/" class="btn btn--primary">
          ← Volver al inicio
        </RouterLink>
        <RouterLink
          v-if="isAuthenticated"
          to="/dashboard"
          class="btn btn--ghost"
        >
          Ir al Dashboard
        </RouterLink>
        <RouterLink
          v-else
          to="/login"
          class="btn btn--ghost"
        >
          Iniciar sesión
        </RouterLink>
      </div>

      <!-- Rutas disponibles -->
      <div class="routes-hint">
        <p class="routes-label">Rutas disponibles:</p>
        <div class="routes-list">
          <RouterLink
            v-for="route in availableRoutes"
            :key="route.path"
            :to="route.path"
            class="route-chip"
          >
            <span>{{ route.icon }}</span>
            {{ route.path }}
          </RouterLink>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const { isAuthenticated } = useAuth()

const currentPath = computed(() => route.path)

const availableRoutes = computed(() => {
  const base = [
    { path: '/',      icon: '🏠' },
    { path: '/login', icon: '🔑' },
  ]
  if (isAuthenticated.value) {
    base.push({ path: '/dashboard', icon: '📊' })
  }
  return base
})
</script>

<style scoped>
.notfound {
  position: relative;
  min-height: calc(100vh - 65px);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 2rem 1rem;
}

/* ── FONDO ── */
.bg { position: absolute; inset: 0; pointer-events: none; }

.bg-orb {
  position: absolute;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(200, 169, 110, 0.06) 0%, transparent 70%);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(200,169,110,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(200,169,110,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* ── 404 FANTASMA ── */
.ghost-number {
  position: absolute;
  font-size: clamp(160px, 28vw, 320px);
  font-weight: 900;
  letter-spacing: -0.05em;
  color: transparent;
  -webkit-text-stroke: 1px rgba(200, 169, 110, 0.06);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  user-select: none;
  white-space: nowrap;
  animation: ghostPulse 4s ease-in-out infinite;
}

@keyframes ghostPulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

/* ── CONTENIDO ── */
.content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1.25rem;
  animation: fadeUp 0.5s ease both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── ICONO ── */
.icon-wrap {
  width: 72px; height: 72px;
  border-radius: 20px;
  background: rgba(200, 169, 110, 0.08);
  border: 1px solid rgba(200, 169, 110, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: iconFloat 3s ease-in-out infinite;
}

@keyframes iconFloat {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-6px); }
}

.icon { font-size: 1.8rem; color: #c8a96e; }

/* ── TEXTOS ── */
.title {
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #e8e4dc;
  margin: 0;
}

.desc {
  color: #5a5550;
  font-size: 0.95rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.route-badge {
  background: rgba(200, 169, 110, 0.1);
  border: 1px solid rgba(200, 169, 110, 0.2);
  color: #c8a96e;
  padding: 0.15rem 0.55rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: monospace;
}

/* ── BOTONES ── */
.actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}

.btn {
  display: inline-flex;
  align-items: center;
  padding: 0.65rem 1.4rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  font-family: inherit;
  text-decoration: none;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.btn--primary {
  background: linear-gradient(135deg, #c8a96e, #a0834e);
  color: #0d0d0f;
}

.btn--primary:hover {
  opacity: 0.9;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(200, 169, 110, 0.2);
}

.btn--ghost {
  background: rgba(255,255,255,0.04);
  color: #9a938c;
  border: 1px solid rgba(255,255,255,0.08);
}

.btn--ghost:hover {
  background: rgba(255,255,255,0.08);
  color: #e8e4dc;
}

/* ── RUTAS DISPONIBLES ── */
.routes-hint {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.routes-label {
  font-size: 0.78rem;
  color: #3a3530;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0;
}

.routes-list {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.route-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.85rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 999px;
  font-size: 0.8rem;
  font-family: monospace;
  color: #6b6560;
  text-decoration: none;
  transition: all 0.2s ease;
}

.route-chip:hover {
  border-color: rgba(200, 169, 110, 0.25);
  color: #c8a96e;
  background: rgba(200, 169, 110, 0.06);
}
</style>
