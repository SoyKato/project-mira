<template>
  <div class="home">
    <!-- HERO: Título principal + Cámara -->
    <section class="hero-section">
      <div class="hero-content">
        <div class="vcr-badge">
          <span class="blink">● REC</span>
          <span>MIRA-SECURITY</span>
        </div>
        
        <h1 class="hero-title">
          <span>DETECT</span>
          <span>PROTECT</span>
        </h1>
        
        <div class="hero-stats">
          <div class="stat">
            <span class="stat-label">MODE</span>
            <span class="stat-value">DETECTION</span>
          </div>
          <div class="stat">
            <span class="stat-label">STATUS</span>
            <span class="stat-value online">ACTIVE</span>
          </div>
        </div>

        <div class="hero-actions">
          <RouterLink 
            v-if="!isAuthenticated" 
            to="/login" 
            class="btn-primary"
          >
            <span class="btn-icon">▶</span>
            INICIAR SESIÓN
          </RouterLink>
          <RouterLink 
            v-else 
            to="/dashboard" 
            class="btn-primary"
          >
            <span class="btn-icon">▶</span>
            IR AL DASHBOARD
          </RouterLink>
        </div>
      </div>

      <!-- CÁMARA / VCR DISPLAY -->
      <div class="camera-container">
        <div class="camera-lens">
          <div class="lens-ring">
            <div class="lens-inner"></div>
          </div>
        </div>
        
        <div class="vcr-display">
          <div class="display-header">
           
          </div>
          
          <div class="display-screen">
            <div class="vcr-clock">12:34:56</div>
           <div class="camera-feed">
              <!-- GIF de cámara de seguridad estilo retro -->
              <img 
                src="https://i.pinimg.com/originals/40/7c/41/407c412f330aeeba7fe72b30efbb8adc.gif" 
                alt="Security camera feed" 
                class="camera-gif"
              >
              <div class="scan-line"></div>
              <div class="detection-box">
                <div class="detection-corner tl"></div>
                <div class="detection-corner tr"></div>
                <div class="detection-corner bl"></div>
                <div class="detection-corner br"></div>
                <span class="detection-text">FACE DETECTED</span>
              </div>
            </div>
            <div class="vcr-mode">
              <span class="mode">MODE: DETECTION</span>
              <span class="status">● REC</span>
            </div>
          </div>
          
          <div class="display-footer">
            <div class="time-counter">00:12:34</div>
            <div>SP</div>
          </div>
        </div>

        <div class="vcr-controls">
          <RouterLink v-if="!isAuthenticated" to="/login" class="vcr-button play">▶</RouterLink>
          <RouterLink v-else to="/dashboard" class="vcr-button play">▶</RouterLink>
          <div class="vcr-button record">●</div>
          <div class="vcr-button stop">■</div>
          <div class="vcr-button eject">▲</div>
        </div>
        
        <div class="vcr-tracking-bar">
          <div class="tracking-label">TRACKING</div>
          <div class="tracking-slider">
            <div class="tracking-level" style="width: 75%"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- FEATURES: Tarjetas -->
    <section class="features-section">
      <div class="section-header">
        <div class="tracking-line">
         
        </div>
      </div>

      <div class="features-grid">
        <article 
          v-for="(feature, idx) in featureList" 
          :key="feature.title"
          class="feature-card"
        >
          <div class="card-stripe"></div>
          <div class="card-header">
            <span class="card-time">{{ padZero(idx + 1) }}:00</span>
            <span class="card-icon">{{ feature.icon }}</span>
          </div>
          <h3 class="card-title">{{ feature.title }}</h3>
          <p class="card-desc">{{ feature.desc }}</p>
          <div class="card-footer">
            <span class="card-track">TRK {{ padZero(idx + 1) }}</span>
            <span class="card-status">●</span>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const { isAuthenticated } = useAuth()

const featureList = [
  { icon: '👁️', title: 'Eye-Scan', desc: 'Detección automática de personas con IA avanzada en tiempo real.' },
  { icon: '📼', title: 'Tape-Log', desc: 'Registro diario con fecha, hora y metadata de cada evento.' },
  { icon: '⚠️', title: 'Alert System', desc: 'Notificaciones instantáneas ante movimiento sospechoso.' },
  { icon: '🎯', title: 'Precision', desc: '99.9% de precisión en detección facial y corporal.' },
  { icon: '☁️', title: 'Cloud Backup', desc: 'Almacenamiento seguro en la nube con encriptación.' },
  { icon: '📊', title: 'Analytics', desc: 'Estadísticas detalladas de actividad y patrones.' }
]

const padZero = (num) => num.toString().padStart(2, '0')
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.home {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0a00 0%, #0f0f1a00 100%);
  font-family: 'Share Tech Mono', 'Courier New', monospace;
}

/* ========== HERO: Título + Cámara ========== */
.hero-section {
  display: flex;
  flex-wrap: wrap;
  min-height: 80vh;
  align-items: center;
  gap: 2rem;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Lado izquierdo - Título */
.hero-content {
  flex: 1;
  min-width: 280px;
  padding: 2rem;
}

.vcr-badge {
  display: flex;
  gap: 2rem;
  font-size: 0.7rem;
  letter-spacing: 2px;
  margin-bottom: 2rem;
  color: #00ffcc;
}

.blink {
  animation: blink 1s infinite;
  color: #ff3366;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.hero-title {
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 900;
  line-height: 1.2;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.hero-title {
  font-size: clamp(2.5rem, 5vw, 3.8rem);
  font-weight: 600;
  line-height: 1.3;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-family: 'Montserrat', 'Helvetica Neue', sans-serif;
  letter-spacing: 6px;
}

.hero-title span {
  color: white;
  text-transform: uppercase;
  display: inline-block;
}

.hero-title span:first-child {
  color: #00ffcc;
}

.hero-stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.stat {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
}

.stat-label {
  color: #888;
  letter-spacing: 2px;
}

.stat-value {
  color: #00ffcc;
}

.stat-value.online {
  color: #00ffcc;
  text-shadow: 0 0 5px #00ffcc;
}

.hero-actions {
  margin-top: 1rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  padding: 1rem 2rem;
  background: rgba(0, 255, 204, 0.1);
  backdrop-filter: blur(10px);
  color: #00ffcc;
  text-decoration: none;
  font-weight: bold;
  letter-spacing: 2px;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  border: 1px solid rgba(0, 255, 204, 0.3);
  border-radius: 12px;
  cursor: pointer;
}

.btn-primary:hover {
  background: rgba(0, 255, 204, 0.2);
  border-color: #00ffcc;
  box-shadow: 0 0 25px rgba(0, 255, 204, 0.3);
  transform: translateY(-2px) scale(1.02);
}

.btn-primary:hover {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(0,255,204,0.5);
}

.btn-icon {
  font-size: 1rem;
}

/* Lado derecho - Cámara */
.camera-container {
  flex: 1;
  min-width: 320px;
  background: rgba(0, 0, 0, 0.127);
  padding: 1.5rem;
  border-radius: 24px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 204, 0.2);
}

.camera-lens {
  display: flex;
  justify-content: center;
  margin-bottom: 1.5rem;
}

.lens-ring {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #00ffcc;
  position: relative;
  animation: pulseRing 2s infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lens-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: radial-gradient(circle, #ff3366);
}

@keyframes pulseRing {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 204, 0.4); }
  50% { box-shadow: 0 0 0 10px rgba(0, 255, 204, 0); }
}

.vcr-display {
  background: #0b61772a;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #2a2a2a;
}



.display-screen {
  padding: 1.5rem;

  
}

.vcr-clock {
  font-size: 0.7rem;
  color: #00ffcc;
  font-family: monospace;
  margin-bottom: 1rem;
  letter-spacing: 2px;
}

.camera-feed {
  background: #918c8c9f;
  height: 200px;
  position: relative;
  overflow: hidden;
  margin-bottom: 1rem;
  border: 1px solid #1a1a1a;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ffcc, transparent);
  animation: scanVertical 3s linear infinite;
}

@keyframes scanVertical {
  0% { top: 0; }
  100% { top: 100%; }
}

.detection-box {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 150px;
  height: 150px;
}

.detection-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: #ff3366;
  border-style: solid;
}

.detection-corner.tl {
  top: 0;
  left: 0;
  border-width: 2px 0 0 2px;
}

.detection-corner.tr {
  top: 0;
  right: 0;
  border-width: 2px 2px 0 0;
}

.detection-corner.bl {
  bottom: 0;
  left: 0;
  border-width: 0 0 2px 2px;
}

.detection-corner.br {
  bottom: 0;
  right: 0;
  border-width: 0 2px 2px 0;
}

.detection-text {
  position: absolute;
  bottom: -25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.6rem;
  color: #ff3366;
  white-space: nowrap;
  animation: blink 1s infinite;
}

.vcr-mode {
  display: flex;
  justify-content: center;
  gap: 2rem;
  font-size: 0.65rem;
}

.mode {
  color: #00ffcc;
  letter-spacing: 2px;
}

.status {
  color: #ff3366;
  animation: blink 1.5s infinite;
}

.display-footer {
  background: #1a1a1a;
  padding: 0.6rem 1.2rem;
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #00ffcc;
  font-family: monospace;
  border-top: 1px solid #2a2a2a;
}

.vcr-controls {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin: 1.5rem 0;
}

.vcr-button {
  width: 44px;
  height: 44px;
  background: #1a1a1a;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  border: 1px solid #3a3a3a;
}

.vcr-button.play {
  background: #00ffcc;
  color: #1a1a1a;
  border-color: #00ffcc;
}

.vcr-button.play:hover {
  transform: scale(1.05);
  background: #00ddbb;
}

.vcr-button.record {
  color: #ff3366;
}

.vcr-button:hover {
  background: #2a2a2a;
  transform: scale(1.05);
}

.vcr-tracking-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tracking-label {
  font-size: 0.65rem;
  color: #00ffcc;
  letter-spacing: 2px;
}

.tracking-slider {
  flex: 1;
  height: 3px;
  background: #2a2a2a;
  border-radius: 3px;
  overflow: hidden;
}

.tracking-level {
  height: 100%;
  background: #00ffcc;
  border-radius: 3px;
}

/* ========== FEATURES SECTION ========== */
.features-section {
  border-radius: 3px;
  padding: 4rem 2rem;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.341));
}

.section-header {
  margin-bottom: 3rem;
}

.tracking-line {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: center;
}

.tracking-line span:first-child,
.tracking-line span:last-child {
  width: 80px;
  height: 1px;
  background: linear-gradient(90deg, transparent, #00e1ff, transparent);
}

.tracking-line span:nth-child(2) {
  color: #00ffcc;
  font-size: 0.7rem;
  letter-spacing: 3px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: #0f0f0f;
  border-radius: 16px;
  padding: 1.5rem;
  position: relative;
  transition: all 0.3s cubic-bezier(0.2, 0.9, 0.4, 1.1);
  border: 1px solid #2a2a2a;
}

.feature-card:hover {
  transform: translateY(-6px);
  background: #141414;
  box-shadow: 0 10px 25px -8px rgba(0, 255, 204, 0.2);
  border-color: #00ffcc;
}

.display-header{
  color: #ffffff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-time {
  font-size: 0.6rem;
  color: #00ffcc;
  font-family: monospace;
  background: rgba(0, 255, 204, 0.1);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.card-icon {
  font-size: 1.8rem;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  margin: 0 0 0.5rem;
  letter-spacing: 1px;
}

.card-desc {
  font-size: 0.7rem;
  color: #aaa;
  line-height: 1.5;
  margin: 0 0 1rem;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.8rem;
  border-top: 1px solid #2a2a2a;
  font-size: 0.6rem;
}

.card-track {
  color: #666;
  font-family: monospace;
}

.card-status {
  color: #ff3366;
  animation: blink 1.5s infinite;
}

/* ========== RESPONSIVE ========== */
@media (max-width: 900px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    padding: 2rem 1rem;
  }
  
  .hero-content {
    text-align: center;
  }
  
  .hero-stats {
    justify-content: center;
  }
  
  .hero-actions {
    display: flex;
    justify-content: center;
  }
  
  .camera-container {
    width: 100%;
  }
}

@media (max-width: 600px) {
  .hero-stats {
    gap: 1rem;
    flex-direction: column;
    align-items: center;
  }
  
  .vcr-controls {
    gap: 0.8rem;
  }
  
  .vcr-button {
    width: 38px;
    height: 38px;
    font-size: 0.9rem;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .detection-box {
    width: 100px;
    height: 100px;
  }
  
  .detection-text {
    font-size: 0.5rem;
    bottom: -20px;
  }
  
  .tracking-line span:first-child,
  .tracking-line span:last-child {
    width: 40px;
  }
}
</style>