<template>
  <div class="app">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">🎯</div>
        <h2>MIRA</h2>
      </div>

      <div class="system-status">
        <div class="status-item">
          <span class="status-dot"></span>
          <span>Sistema Activo</span>
        </div>
        <div class="status-item">
          <span>📹 {{ fps }} FPS</span>
        </div>
        <div class="status-item" v-if="fpsCaptura > 0">
          <span>⚡ {{ fpsCaptura }} fps</span>
        </div>
        <div class="status-item" v-if="sessionId">
          <span>🔑 Sesión activa</span>
        </div>
      </div>

      <div class="user-section">
        <div class="user-header">
          <h3>👥 Personas Registradas</h3>
          <button @click="abrirRegistroIA" class="add-user-btn">+</button>
        </div>
        <div class="user-list">
          <div 
            v-for="(user, index) in usuariosRegistrados" 
            :key="index"
            class="user-item"
            :class="{ selected: usuarioSeleccionado && usuarioSeleccionado.name === user.name }"
          >
            <div class="user-avatar" @click="seleccionarUsuarioRegistrado(user)">
              {{ user.nombre.charAt(0).toUpperCase() }}
            </div>
            <div class="user-info" @click="seleccionarUsuarioRegistrado(user)">
              <div class="user-name">{{ user.nombre }}</div>
            </div>
            <div class="user-actions">
              <button @click="editarUsuario(user)" class="user-edit" title="Editar">✏️</button>
              <button @click="eliminarUsuario(user)" class="user-delete" title="Eliminar">🗑️</button>
            </div>
          </div>
          <div v-if="usuariosRegistrados.length === 0" class="empty-users">
            <span>No hay personas registradas</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main">
      <header class="header">
        <div class="title">
          <h1>Monitoreo Inteligente</h1>
          <p>Detección facial en tiempo real</p>
        </div>
        <div class="datetime">
          <span>📅 {{ fechaActual }}</span>
          <button @click="cerrarSesion" class="logout-btn">🚪 Salir</button>
        </div>
      </header>

      <div class="main-grid">
        <!-- Video Stream -->
        <div class="video-section">
          <div class="video-header">
            <div class="live-indicator">
              <span class="live-dot"></span>
              <span>EN VIVO</span>
            </div>
            <div class="video-controls">
              <select v-model="camaraSeleccionada" @change="cambiarCamara" class="camara-select">
                <option v-for="cam in camarasDisponibles" :key="cam.deviceId" :value="cam.deviceId">
                  📷 {{ cam.label || `Cámara ${cam.index + 1}` }}
                </option>
              </select>
              <button @click="alternarCamara" class="camara-btn" :class="{ active: camaraEncendida }">
                {{ camaraEncendida ? '🔴 Apagar' : '🟢 Prender' }}
              </button>
            </div>
          </div>
          <div class="video-container">
            <video 
              ref="videoLocal"
              autoplay 
              playsinline 
              muted
              class="video-stream"
              v-show="camaraEncendida"
            ></video>
            <div v-show="!camaraEncendida" class="video-off">
              <div class="off-content">
                <div class="off-icon">📷</div>
                <p>Cámara apagada</p>
                <small>Presiona "Prender" para activar</small>
              </div>
            </div>
            <canvas 
              ref="canvasOverlay" 
              :width="640" 
              :height="480"
              class="overlay"
            ></canvas>
          </div>
          
          <div v-if="estadoVerificacion" class="verification-status">
            <div class="verification-progress">
              <span>🎯 Verificando: </span>
              <span class="progress-count">{{ estadoVerificacion }}</span>
            </div>
          </div>
          <div v-if="ultimoReconocimiento && ultimoReconocimiento.results && ultimoReconocimiento.results.length" class="diagnostic-panel">
            <h3>🔍 Diagnóstico de rostros</h3>
            <div class="diagnostic-item" v-for="(face, index) in ultimoReconocimiento.results" :key="index">
              <span class="diagnostic-name">
                {{ face.name || (face.reason === 'verifying' ? 'Verificando' : 'Desconocido') }}
              </span>
              <span class="diagnostic-score" v-if="face.confidence !== undefined && face.confidence !== null">
                · score {{ face.confidence.toFixed(3) }}
              </span>
              <span class="diagnostic-score" v-else-if="face.average_score !== undefined && face.average_score !== null">
                · avg {{ face.average_score.toFixed(3) }}
              </span>
              <span class="diagnostic-score" v-else-if="face.top_score !== undefined && face.top_score !== null">
                · top {{ face.top_score.toFixed(3) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Alertas de Desconocidos -->
        <div class="alerts-section">
          <div class="section-header">
            <h3>⚠️ Alertas</h3>
            <span class="alert-count">{{ historial.length }}</span>
          </div>
          <div class="alerts-list" ref="historialLista">
            <div 
              v-for="(alert, index) in historial" 
              :key="index"
              class="alert-item"
              :class="{ clickable: !!alert.imageUrl }"
              @click="alert.imageUrl && abrirImagenAlerta(alert)"
            >
              <div class="alert-icon">❓</div>
              <div class="alert-details">
                <div class="alert-time">{{ alert.hora }}</div>
                <div class="alert-date">{{ alert.fecha }}</div>
                <div v-if="alert.title" class="alert-title">{{ alert.title }}</div>
              </div>
            </div>
            <div v-if="historial.length === 0" class="no-alerts">
              <span>✅ Sin alertas</span>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal de Registro IA -->
    <div v-if="modalRegistroVisible" class="modal" @click.self="cerrarModalRegistro">
      <div class="modal-content modal-registro">
        <div class="modal-header">
          <h3>📸 Registrar Nueva Persona</h3>
          <button @click="cerrarModalRegistro" class="modal-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Nombre de la persona:</label>
            <input 
              v-model="nombreRegistro" 
              type="text" 
              placeholder="Ej: Juan Pérez" 
              class="form-input"
              @keyup.enter="iniciarRegistro"
            >
          </div>
          
          <div class="registro-preview">
            <video 
              ref="registroVideo"
              autoplay 
              playsinline
              class="registro-video"
              v-show="!registroActivo && !registroCompletado"
            ></video>
            <div v-if="registroActivo" class="registro-activo">
              <div class="countdown-circle">
                <span>{{ tiempoRestante }}</span>
              </div>
              <p>📸 Capturando fotos...</p>
              <small>Muévete lentamente para diferentes ángulos</small>
              <div class="fotos-capturadas">
                📸 Fotos: {{ fotosGuardadas }}/{{ maxFotos }}
              </div>
            </div>
            <div v-if="registroCompletado" class="registro-completado">
              <div class="success-icon">✅</div>
              <p>¡Registro completado!</p>
              <small>{{ fotosGuardadas }} fotos guardadas</small>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="cerrarModalRegistro" class="btn-secondary">Cancelar</button>
          <button 
            @click="iniciarRegistro" 
            :disabled="!nombreRegistro.trim() || registroActivo" 
            class="btn-primary"
          >
            {{ registroActivo ? `Registrando (${fotosGuardadas}/${maxFotos})...` : 'Iniciar Registro' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { supabase } from '@/lib/supabaseClient'

export default {
  name: 'DashboardView',
  data() {
    return {
      currentUser: null,
      currentUserId: null,
      loadingUser: true,
      
      streamLocal: null,
      registroStream: null,
      capturaInterval: null,
      camaraEncendida: true,
      camarasDisponibles: [],
      camaraSeleccionada: null,
      
      reconociendo: false,
      ultimoReconocimiento: null,
      deteccionesActuales: [],
      usuariosRegistrados: [],
      historial: [],
      fotosCapturadasLista: [],
      
      fps: 0,
      frameCount: 0,
      ultimoFrameTime: Date.now(),
      fechaActual: new Date().toLocaleString(),
      usuarioSeleccionado: null,
      
      sessionId: null,
      estadoVerificacion: null,
      
      // Modal registro IA
      modalRegistroVisible: false,
      registroActivo: false,
      registroCompletado: false,
      nombreRegistro: '',
      tiempoRestante: 20,
      fotosGuardadas: 0,
      maxFotos: 100,
      registroInterval: null,
      captureInterval: null,
      
      apiUrl: 'http://localhost:8000'
    }
  },
  
  async mounted() {
    await this.obtenerUsuarioActual()
    
    if (this.currentUserId) {
      this.sessionId = this.generarSessionId()
      console.log('🔑 Sesión creada:', this.sessionId)
      
      await this.listarCamaras()
      await this.cargarPersonasRegistradas()
      await this.obtenerHistorialDesconocidos()
      this.actualizarFecha()
      this.iniciarCapturaPeriodica()
    } else {
      this.$router.push('/login')
    }
  },
  
  beforeUnmount() {
    if (this.capturaInterval) clearInterval(this.capturaInterval)
    if (this.registroInterval) clearInterval(this.registroInterval)
    if (this.captureInterval) clearInterval(this.captureInterval)
    if (this.streamLocal) {
      this.streamLocal.getTracks().forEach(track => track.stop())
    }
    if (this.registroStream) {
      this.registroStream.getTracks().forEach(track => track.stop())
    }
  },
  
  methods: {
    generarSessionId() {
      return `session_${this.currentUserId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    },
    
    // =========================================
    // AUTENTICACIÓN
    // =========================================
    async obtenerUsuarioActual() {
      try {
        const { data: { user }, error: userError } = await supabase.auth.getUser()
        
        if (userError) throw userError
        
        if (user) {
          let { data: registro, error: registroError } = await supabase
            .from('registro')
            .select('id, nombre, email')
            .eq('email', user.email)
            .maybeSingle()
          
          if (registroError && registroError.code !== 'PGRST116') {
            console.error('Error buscando registro:', registroError)
          }
          
          if (!registro) {
            const nombre = user.user_metadata?.full_name || user.email?.split('@')[0] || 'Usuario'
            
            const { data: newRegistro, error: insertError } = await supabase
              .from('registro')
              .insert({
                nombre: nombre,
                email: user.email
              })
              .select()
              .single()
            
            if (insertError) {
              console.error('Error creando registro:', insertError)
              return
            }
            
            registro = newRegistro
            console.log('✅ Nuevo registro creado:', registro)
          }
          
          if (registro) {
            this.currentUserId = registro.id
            this.currentUser = registro
            console.log('✅ Usuario autenticado - ID:', this.currentUserId)
          }
        } else {
          console.log('No hay usuario autenticado')
          this.$router.push('/login')
        }
      } catch (error) {
        console.error('Error:', error)
      } finally {
        this.loadingUser = false
      }
    },
    
    cerrarSesion() {
      supabase.auth.signOut()
      this.$router.push('/login')
    },
    
    // =========================================
    // CÁMARA
    // =========================================
    async listarCamaras() {
      try {
        await navigator.mediaDevices.getUserMedia({ video: true })
        
        const devices = await navigator.mediaDevices.enumerateDevices()
        const videoDevices = devices.filter(device => device.kind === 'videoinput')
        
        this.camarasDisponibles = videoDevices.map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Cámara ${index + 1}`,
          index: index
        }))
        
        if (this.camarasDisponibles.length > 0 && !this.camaraSeleccionada) {
          this.camaraSeleccionada = this.camarasDisponibles[0].deviceId
          await this.iniciarCamaraLocal()
        }
      } catch (error) {
        console.error('Error:', error)
        this.camaraEncendida = false
      }
    },
    
    async iniciarCamaraLocal() {
      try {
        if (this.streamLocal) {
          this.streamLocal.getTracks().forEach(track => track.stop())
        }
        
        const constraints = {
          video: this.camaraSeleccionada ? {
            deviceId: { exact: this.camaraSeleccionada },
            width: { exact: 640 },
            height: { exact: 480 }
          } : {
            width: { exact: 640 },
            height: { exact: 480 }
          }
        }
        
        this.streamLocal = await navigator.mediaDevices.getUserMedia(constraints)
        const videoElement = this.$refs.videoLocal
        if (videoElement) {
          videoElement.srcObject = this.streamLocal
        }
        this.camaraEncendida = true
      } catch (error) {
        console.error('Error:', error)
        try {
          const constraints = { video: true }
          this.streamLocal = await navigator.mediaDevices.getUserMedia(constraints)
          const videoElement = this.$refs.videoLocal
          if (videoElement) {
            videoElement.srcObject = this.streamLocal
          }
          this.camaraEncendida = true
        } catch (fallbackError) {
          console.error('Error:', fallbackError)
          this.camaraEncendida = false
        }
      }
    },
    
    async cambiarCamara() {
      if (this.camaraEncendida) {
        await this.iniciarCamaraLocal()
      }
    },
    
    alternarCamara() {
      if (this.camaraEncendida) {
        if (this.streamLocal) {
          this.streamLocal.getTracks().forEach(track => track.stop())
          this.streamLocal = null
        }
        if (this.capturaInterval) {
          clearInterval(this.capturaInterval)
          this.capturaInterval = null
        }
        this.camaraEncendida = false
      } else {
        this.iniciarCamaraLocal()
        this.iniciarCapturaPeriodica()
      }
    },
    
    // =========================================
    // CAPTURA Y RECONOCIMIENTO
    // =========================================
    iniciarCapturaPeriodica() {
      if (this.capturaInterval) clearInterval(this.capturaInterval)
      
      this.capturaInterval = setInterval(() => {
        if (this.camaraEncendida && !this.reconociendo && !this.registroActivo) {
          this.capturarYReconocer()
        }
      }, 500)
    },
    
    async capturarYReconocer() {
      const video = this.$refs.videoLocal
      if (!video || video.readyState !== video.HAVE_ENOUGH_DATA) return
      
      this.reconociendo = true
      
      try {
        const canvas = document.createElement('canvas')
        canvas.width = video.videoWidth || 640
        canvas.height = video.videoHeight || 480
        const ctx = canvas.getContext('2d')
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8))
        
        const formData = new FormData()
        formData.append('user_id', this.currentUserId)
        formData.append('file', blob, 'frame.jpg')
        formData.append('session_id', this.sessionId)
        
        const response = await fetch(`${this.apiUrl}/api/recognize`, {
          method: 'POST',
          body: formData
        })
        
        const result = await response.json()
        this.ultimoReconocimiento = result
        const faces = result.results || []
        this.dibujarRectangulo(faces)

        const verifyingFace = faces.find(face => face.reason === 'verifying')
        this.estadoVerificacion = verifyingFace ? `${verifyingFace.verify_count || 0}/${verifyingFace.verify_required || 2}` : null

        const unknownFace = faces.find(face => face.reason === 'unknown_face' && face.unknown_image_url)
        if (unknownFace) {
          await this.obtenerHistorialDesconocidos()
        }

        this.calcularFPS()
        
      } catch (error) {
        console.error('Error:', error)
      } finally {
        this.reconociendo = false
      }
    },
    
    dibujarRectangulo(faces) {
      const canvas = this.$refs.canvasOverlay
      const video = this.$refs.videoLocal
      if (!canvas) return

      if (video && video.videoWidth && video.videoHeight) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
      }

      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      faces.forEach(face => {
        const [x1, y1, x2, y2] = face.bbox
        const isRecognized = face.recognized
        const isVerifying = face.reason === 'verifying'
        const color = isRecognized ? '#10b981' : '#ef4444'
        const score = face.confidence ?? face.average_score ?? face.top_score
        let texto = 'Desconocido'

        if (isRecognized) {
          texto = face.name || 'Reconocido'
          if (score !== undefined && score !== null) {
            texto += ` · ${score.toFixed(3)}`
          }
        } else if (isVerifying) {
          const count = face.verify_count || 0
          const required = face.verify_required || 3
          texto = `Verificando ${count}/${required}`
          if (score !== undefined && score !== null) {
            texto += ` · ${score.toFixed(3)}`
          }
        } else if (score !== undefined && score !== null) {
          texto = `Desconocido · ${score.toFixed(3)}`
        }

        ctx.strokeStyle = color
        ctx.lineWidth = 3
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

        ctx.font = 'bold 16px "Segoe UI"'
        const medidasTexto = ctx.measureText(texto)
        const anchoTexto = medidasTexto.width + 16

        ctx.fillStyle = isRecognized ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.9)'
        ctx.fillRect(x1, y1 - 32, anchoTexto, 32)

        ctx.fillStyle = '#ffffff'
        ctx.fillText(texto, x1 + 8, y1 - 10)
      })
    },
    
    calcularFPS() {
      this.frameCount++
      const ahora = Date.now()
      const delta = ahora - this.ultimoFrameTime
      
      if (delta >= 1000) {
        this.fps = this.frameCount
        this.frameCount = 0
        this.ultimoFrameTime = ahora
      }
    },
    
    agregarAlerta({ imageUrl = null, title = 'Rostro desconocido' } = {}) {
      if (imageUrl && this.historial.some(item => item.imageUrl === imageUrl)) {
        return
      }

      const ahora = new Date()
      this.historial.unshift({
        hora: ahora.toLocaleTimeString(),
        fecha: ahora.toLocaleDateString(),
        imageUrl,
        title
      })
      
      if (this.historial.length > 50) {
        this.historial.pop()
      }
    },

    abrirImagenAlerta(alert) {
      if (alert.imageUrl) {
        window.open(alert.imageUrl, '_blank')
      }
    },
    
    // =========================================
    // REGISTRO - VERSIÓN SIMPLE Y CONFIABLE
    // =========================================
    async abrirRegistroIA() {
      this.modalRegistroVisible = true
      this.registroActivo = false
      this.registroCompletado = false
      this.nombreRegistro = ''
      this.fotosGuardadas = 0
      this.fotosCapturadasLista = []
      this.tiempoRestante = 15
      
      setTimeout(async () => {
        try {
          if (this.registroStream) {
            this.registroStream.getTracks().forEach(track => track.stop())
          }
          const stream = await navigator.mediaDevices.getUserMedia({ video: true })
          this.registroStream = stream
          const videoElement = this.$refs.registroVideo
          if (videoElement) {
            videoElement.srcObject = stream
          }
        } catch (error) {
          console.error('Error:', error)
        }
      }, 100)
    },
    
    cerrarModalRegistro() {
      if (this.registroInterval) {
        clearInterval(this.registroInterval)
        this.registroInterval = null
      }
      if (this.captureInterval) {
        clearInterval(this.captureInterval)
        this.captureInterval = null
      }
      this.modalRegistroVisible = false
      this.fotosCapturadasLista = []
      if (this.registroStream) {
        this.registroStream.getTracks().forEach(track => track.stop())
        this.registroStream = null
      }
    },
    
    async iniciarRegistro() {
      if (!this.nombreRegistro.trim()) {
        alert('Por favor ingresa un nombre')
        return
      }

      const video = this.$refs.registroVideo
      if (!video) return

      await new Promise(resolve => {
        if (video.readyState >= 2) {
          resolve()
        } else {
          video.onloadeddata = () => resolve()
        }
      })

      this.registroActivo = true
      this.registroCompletado = false
      this.fotosGuardadas = 0
      this.fotosCapturadasLista = []
      this.tiempoRestante = 20

      console.log("🚀 Iniciando captura por 20 segundos")
      
      // Capturar cada 500ms (2 fps) para evitar fotos repetidas
      this.captureInterval = setInterval(async () => {
        if (!this.registroActivo) return
        if (this.fotosGuardadas >= this.maxFotos) {
          console.log("📸 Límite de fotos alcanzado")
          return
        }
        
        try {
          const canvas = document.createElement('canvas')
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          const ctx = canvas.getContext('2d')
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
          
          const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8))
          
          if (blob) {
            this.fotosCapturadasLista.push(blob)
            this.fotosGuardadas = this.fotosCapturadasLista.length
            console.log(`📸 Foto ${this.fotosGuardadas}/${this.maxFotos}`)
          }
        } catch (err) {
          console.error("❌ Error capturando:", err)
        }
      }, 500)
      
      // Temporizador de 15 segundos
      const countdownInterval = setInterval(() => {
        this.tiempoRestante--
        if (this.tiempoRestante <= 0) {
          clearInterval(countdownInterval)
        }
      }, 1000)
      
      // Finalizar después de 15 segundos
      setTimeout(async () => {
        clearInterval(this.captureInterval)
        clearInterval(countdownInterval)
        this.registroActivo = false
        
        const fotos = this.fotosCapturadasLista
        console.log(`📦 TOTAL FOTOS: ${fotos.length}`)
        
        if (fotos.length === 0) {
          this.mostrarMensaje('❌ No se capturaron fotos', 'error')
          this.registroActivo = false
          return
        }
        
        try {
          const formData = new FormData()
          formData.append('name', this.nombreRegistro)
          
          fotos.forEach((blob, i) => {
            formData.append('files', blob, `foto_${Date.now()}_${i}.jpg`)
          })
          
          console.log(`🚀 ENVIANDO ${fotos.length} FOTOS...`)
          
          const response = await fetch(`${this.apiUrl}/api/register/${this.currentUserId}`, {
            method: 'POST',
            body: formData
          })
          
          const result = await response.json()
          console.log("📥 RESPUESTA:", result)
          
          if (result.success) {
            this.registroCompletado = true
            this.mostrarMensaje(`✅ ${this.nombreRegistro} registrado con ${result.images_saved} fotos`, 'exito')
            await this.cargarPersonasRegistradas()
          } else {
            this.mostrarMensaje(result.message || 'Error registrando', 'error')
          }
          
        } catch (error) {
          console.error("❌ ERROR:", error)
          this.mostrarMensaje('Error registrando', 'error')
        }
        
        setTimeout(() => {
          this.cerrarModalRegistro()
        }, 2000)
        
      }, 30000)
    },
    
    // =========================================
    // GESTIÓN DE PERSONAS REGISTRADAS
    // =========================================
    async cargarPersonasRegistradas() {
      try {
        const response = await fetch(`${this.apiUrl}/api/known-faces/${this.currentUserId}`)
        const data = await response.json()
        this.usuariosRegistrados = data.faces || []
      } catch (error) {
        console.error('Error:', error)
        this.usuariosRegistrados = []
      }
    },
    
    async obtenerHistorialDesconocidos(limit = 50) {
      if (!this.currentUserId) return

      try {
        const response = await fetch(`${this.apiUrl}/api/unknown-faces-history/${this.currentUserId}?limit=${limit}`)
        const data = await response.json()

        this.historial = (data.unknown_faces || []).map(item => {
          const fecha = new Date(item.timestamp)
          const imageUrl = item.face_image_path?.startsWith('http')
            ? item.face_image_path
            : `${this.apiUrl}${item.face_image_path}`

          return {
            id: item.id,
            imageUrl,
            title: item.confidence !== null && item.confidence !== undefined
              ? `Rostro desconocido · ${Number(item.confidence).toFixed(3)}`
              : 'Rostro desconocido',
            fecha: fecha.toLocaleDateString(),
            hora: fecha.toLocaleTimeString(),
            revisado: item.is_reviewed
          }
        })
      } catch (error) {
        console.error('Error cargando historial:', error)
        this.historial = []
      }
    },

    async editarUsuario(user) {
      const nuevoNombre = prompt('Ingrese el nuevo nombre:', user.nombre)
      if (nuevoNombre && nuevoNombre !== user.nombre) {
        this.mostrarMensaje('Función en desarrollo', 'info')
      }
    },
    
    async eliminarUsuario(user) {
      if (confirm(`¿Eliminar a "${user.nombre}" permanentemente?`)) {
        try {
          const response = await fetch(`${this.apiUrl}/api/delete-person/${this.currentUserId}/${encodeURIComponent(user.name)}`, {
            method: 'DELETE'
          })
          
          const result = await response.json()
          
          if (result.success) {
            this.mostrarMensaje(`✅ ${result.message}`, 'exito')
            await this.cargarPersonasRegistradas()
          } else {
            this.mostrarMensaje(result.message || 'Error al eliminar', 'error')
          }
        } catch (error) {
          console.error('Error:', error)
          this.mostrarMensaje('Error al eliminar persona', 'error')
        }
      }
    },
    
    seleccionarUsuarioRegistrado(user) {
      if (this.usuarioSeleccionado && this.usuarioSeleccionado.name === user.name) {
        this.usuarioSeleccionado = null
      } else {
        this.usuarioSeleccionado = user
        this.mostrarMensaje(`Seleccionado: ${user.nombre}`, 'info')
      }
    },
    
    mostrarMensaje(mensaje, tipo) {
      const toast = document.createElement('div')
      toast.className = `toast ${tipo}`
      toast.textContent = mensaje
      document.body.appendChild(toast)
      
      setTimeout(() => toast.classList.add('show'), 100)
      setTimeout(() => {
        toast.classList.remove('show')
        setTimeout(() => document.body.removeChild(toast), 300)
      }, 3000)
    },
    
    actualizarFecha() {
      setInterval(() => {
        this.fechaActual = new Date().toLocaleString()
      }, 1000)
    }
  }
}
</script>

<style scoped>
/* ESTILOS - Igual que antes */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  display: flex;
  height: 100vh;
  background: #0a0e27;
  font-family: 'Segoe UI', 'Inter', sans-serif;
}

.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #0f122e 0%, #0a0e27 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 28px;
}

.logo h2 {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.system-status {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 10px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.user-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 4px;
}

.user-header h3 {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.add-user-btn {
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  color: #fff;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-user-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
}

.user-list {
  flex: 1;
  overflow-y: auto;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  margin-bottom: 6px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.user-item:hover {
  background: rgba(102, 126, 234, 0.15);
}

.user-item.selected {
  background: rgba(102, 126, 234, 0.2);
  border-color: #667eea;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  font-size: 14px;
}

.user-info {
  flex: 1;
  cursor: pointer;
}

.user-name {
  color: #fff;
  font-weight: 600;
  font-size: 12px;
}

.user-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.user-edit, .user-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.user-edit {
  color: #667eea;
}

.user-edit:hover {
  background: rgba(102, 126, 234, 0.2);
  transform: scale(1.1);
}

.user-delete {
  color: #ef4444;
}

.user-delete:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(1.1);
}

.empty-users {
  text-align: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px 28px;
  overflow-y: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title h1 {
  color: #fff;
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 2px;
}

.title p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.datetime {
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 14px;
  border-radius: 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.logout-btn {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.3);
}

.main-grid {
  display: grid;
  grid-template-columns: 1.3fr 260px;
  gap: 20px;
  flex: 1;
  min-height: 0;
  margin-bottom: 16px;
}

.video-section {
  background: rgba(0, 0, 0, 0.5);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  position: relative;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 18px;
  background: rgba(0, 0, 0, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dot {
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

.live-indicator span {
  color: #ef4444;
  font-weight: bold;
  font-size: 11px;
  letter-spacing: 1px;
}

.video-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.camara-select {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  outline: none;
}

.camara-select:hover {
  background: rgba(255, 255, 255, 0.15);
}

.camara-select option {
  background: #0f122e;
}

.camara-btn {
  padding: 4px 14px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 11px;
  transition: all 0.3s;
}

.camara-btn.active {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
  color: #10b981;
}

.camara-btn:hover {
  transform: translateY(-1px);
}

.video-container {
  position: relative;
  flex: 1;
  background: #000;
  min-height: 480px;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-off {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0e27;
  text-align: center;
}

.off-content {
  text-align: center;
}

.off-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.off-content p {
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 6px;
  font-size: 13px;
}

.off-content small {
  color: rgba(255, 255, 255, 0.3);
  font-size: 10px;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: auto;
  cursor: crosshair;
}

.verification-status {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 6px 12px;
  background: rgba(102, 126, 234, 0.8);
  border-radius: 8px;
  font-size: 11px;
  color: #fff;
  z-index: 10;
}

.verification-progress {
  display: flex;
  gap: 6px;
  align-items: center;
}

.progress-count {
  font-weight: bold;
  color: #10b981;
}

.diagnostic-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 10px;
  color: #ccc;
  z-index: 10;
  font-family: monospace;
  max-width: 220px;
  backdrop-filter: blur(4px);
  border-left: 3px solid #667eea;
}

.diagnostic-panel h3 {
  font-size: 10px;
  margin: 0 0 4px 0;
  color: #fff;
}

.diagnostic-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 9px;
  line-height: 1.4;
}

.diagnostic-name {
  color: #facc15;
}

.diagnostic-score {
  color: #4ade80;
}

.recognition-result {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10;
}

.recognition-result.success {
  background: rgba(16, 185, 129, 0.9);
}

.recognition-result.warning {
  background: rgba(239, 68, 68, 0.9);
}

.result-icon {
  font-size: 24px;
}

.result-text {
  flex: 1;
  color: #fff;
}

.result-text strong {
  display: block;
  font-size: 14px;
}

.result-text span {
  font-size: 11px;
  opacity: 0.9;
}

.alerts-section {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.section-header h3 {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.alert-count {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}

.alerts-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.alert-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
  margin-bottom: 6px;
  border-left: 3px solid #ef4444;
  transition: all 0.2s;
  cursor: pointer;
}

.alert-item {
  transition: all 0.2s;
}

.alert-item.clickable {
  cursor: pointer;
}

.alert-item:hover {
  background: rgba(239, 68, 68, 0.15);
  transform: translateX(-3px);
}

.alert-title {
  color: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  margin-top: 4px;
}

.alert-icon {
  font-size: 24px;
}

.alert-details {
  flex: 1;
}

.alert-time {
  color: #fff;
  font-weight: 600;
  font-size: 12px;
  margin-bottom: 2px;
}

.alert-date {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.no-alerts {
  text-align: center;
  padding: 30px 16px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
}

/* Modal Registro IA */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-registro {
  max-width: 500px;
}

.modal-content {
  background: #0f122e;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  color: #fff;
}

.modal-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
  font-size: 13px;
}

.form-input {
  width: 100%;
  padding: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #fff;
}

.registro-preview {
  text-align: center;
  min-height: 300px;
}

.registro-video {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.registro-activo {
  text-align: center;
  padding: 20px;
}

.countdown-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.countdown-circle span {
  font-size: 36px;
  font-weight: bold;
  color: #fff;
}

.registro-activo p {
  color: #fff;
  margin-bottom: 8px;
}

.registro-activo small {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.fotos-capturadas {
  margin-top: 20px;
  padding: 8px 16px;
  background: rgba(16, 185, 129, 0.2);
  border-radius: 20px;
  display: inline-block;
  color: #10b981;
  font-weight: bold;
}

.registro-completado {
  text-align: center;
  padding: 40px 20px;
}

.success-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.registro-completado p {
  color: #fff;
  font-size: 18px;
  margin-bottom: 8px;
}

.registro-completado small {
  display: block;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-primary, .btn-secondary {
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary {
  background: linear-gradient(135deg, #10b981, #059669);
  border: none;
  color: #fff;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 20px;
  border-radius: 8px;
  background: #1f2937;
  color: #fff;
  z-index: 1000;
  opacity: 0;
  transform: translateY(100px);
  transition: all 0.3s;
  font-size: 13px;
}

.toast.show {
  opacity: 1;
  transform: translateY(0);
}

.toast.exito { background: #10b981; }
.toast.error { background: #ef4444; }
.toast.info { background: #667eea; }

::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>