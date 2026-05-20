import os
import cv2
import time
import shutil
import threading
import queue
import numpy as np
import tensorflow as tf
from pathlib import Path

from datetime import datetime
from collections import deque
from ultralytics import YOLO
from deepface import DeepFace

# =========================================
# MODELO DE EMBEDDINGS
# =========================================
MODEL_NAME = "ArcFace"
FACE_RECOGNITION_MODEL = DeepFace.build_model(MODEL_NAME)

# =======================================================================
# PROYECTO: MIRA | Monitoreo Inteligente de Reconocimiento Automatizado
# =======================================================================

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

gpus = tf.config.experimental.list_physical_devices("GPU")

if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print("✅ TensorFlow usando GPU")
    except RuntimeError as e:
        print(e)

print("Iniciando Sistema....")

# =========================================
# MODELOS
# =========================================

model = YOLO("face_yolov8m.pt").to("cuda")

# =========================================
# PARAMETROS OPTIMIZADOS PARA RAPIDEZ
# =========================================

# SCORES - Balanceados para rapidez y precisión
THRESHOLD = 0.75          # 75% de similitud mínima
RATIO_THRESHOLD = 0.22    # Diferencia del 22% con el segundo mejor
MIN_SCORE = 0.72          # Mínimo absoluto 72%

# MAXIMO DE EMBEDDINGS POR PERSONA
MAX_EMBEDDINGS = 200

# FILTROS - Permisivos para más rapidez
SHARPNESS_FILTER = 20     # Más permisivo
MIN_FACE_SIZE = 40        # Rostro más pequeño

# =========================================
# LÓGICA DE VERIFICACIÓN RÁPIDA
# =========================================
MOTION_MODE = True
VERIFY_REQUIRED = 2              # 2 aciertos necesarios
VERIFY_WINDOW = 5.0              # 5 SEGUNDOS (reducido de 6)
MOTION_SPEED_THRESHOLD = 15

# OPTIMIZACIONES ADICIONALES
EMBEDDING_SKIP_FRAMES = 1        # Procesar cada frame
MAX_BUFFER = 3                    # Buffer más pequeño (antes 4)
# =========================================

# CACHE DE IDENTIDAD
FAST_RECHECK_TIME = 1.0           # Reducido para respuesta más rápida

# TAMAÑO FACENET
FACE_SIZE = 160

# RESOLUCION DETECTOR
DETECTION_SIZE = 736

# TRACKING
LOST_TRACK_TOLERANCE = 5.0
MEMORY_DISTANCE_THRESHOLD = 0.85

# =========================================
# NUEVA ESTRUCTURA DE CARPETAS MULTI-USUARIO
# =========================================

# Directorio base para datos de usuarios
BASE_DIR = Path(__file__).parent
USERS_DATA_DIR = BASE_DIR / "users_data"
USERS_DATA_DIR.mkdir(exist_ok=True)

# =========================================
# UNKNOWN FACE LOGGER (Modificado para multi-usuario)
# =========================================

class UnknownFaceLogger:
    
    def __init__(self, save_folder):
        self.save_folder = Path(save_folder)
        self.save_folder.mkdir(parents=True, exist_ok=True)
        self.last_save_time = {}
        self.save_cooldown = 5.0
        
    def save_unknown_face(self, face_img, track_id, current_time, reason="desconocido"):
        now = datetime.now()
        filename = now.strftime(f"%m_%d_%Y_%H_%M_{reason}.png")
        filepath = self.save_folder / filename
        
        if filepath.exists():
            filename = now.strftime(f"%m_%d_%Y_%H_%M_%S_{reason}.png")
            filepath = self.save_folder / filename
        
        cv2.imwrite(str(filepath), face_img)
        self.last_save_time[track_id] = current_time
        return str(filepath)

# =========================================
# RECOGNIZER - MODO RAPIDO CON MULTI-USUARIO
# =========================================

class SimpleFaceRecognizer:

    def __init__(self, user_id: str = None):
        """
        user_id: UUID del usuario desde Supabase
        Si no se proporciona, usa las carpetas locales originales (modo demo)
        """
        self.user_id = user_id
        
        # Configurar rutas según modo
        if user_id:
            # Modo multi-usuario
            self.user_dir = USERS_DATA_DIR / user_id
            self.known_faces_dir = self.user_dir / "known_faces"
            self.unknown_faces_dir = self.user_dir / "unknown_faces"
            self.motion_captures_dir = self.user_dir / "motion_captures"
            self.temp_scan_dir = self.user_dir / "temp_scan"
            print(f"📁 Modo multi-usuario: {user_id}")
        else:
            # Modo local (original) - para pruebas
            self.known_faces_dir = Path("known_faces")
            self.unknown_faces_dir = Path("unknown_faces")
            self.motion_captures_dir = Path("motion_captures")
            self.temp_scan_dir = Path("temp_scan")
            print(f"📁 Modo local (demo)")
        
        # Crear carpetas
        for d in [self.known_faces_dir, self.unknown_faces_dir, 
                  self.motion_captures_dir, self.temp_scan_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Inicializar variables
        self.known_embeddings = {}
        self.embedding_buffer = {}
        self.stable_id = {}           # ID confirmados por track
        
        # Contadores por track ID
        self.verify_counter = {}
        self.verify_start_time = {}
        self.verified_identity = {}
        self.verification_completed = {}
        
        # Detección de movimiento
        self.prev_position = {}
        self.motion_detected = {}
        
        self.last_seen_time = {}
        self.unknown_start_time = {}
        self.unknown_extended_time = {}
        self.unknown_alert_cooldown = {}
        self.pending_results = {}
        
        self.unknown_logger = UnknownFaceLogger(self.unknown_faces_dir)
        
        self.embedding_queue = queue.Queue(maxsize=64)
        self.result_queue = queue.Queue()

        self.load_database()
        threading.Thread(target=self.embedding_worker, daemon=True).start()

    # =========================================
    # DETECTAR MOVIMIENTO
    # =========================================
    
    def is_moving(self, track_id, current_position, current_time):
        if track_id not in self.prev_position:
            self.prev_position[track_id] = current_position
            self.motion_detected[track_id] = False
            return False
        
        prev_x, prev_y = self.prev_position[track_id]
        curr_x, curr_y = current_position
        
        distance = np.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
        self.prev_position[track_id] = current_position
        
        is_moving_now = distance > MOTION_SPEED_THRESHOLD
        
        if track_id in self.motion_detected:
            if is_moving_now != self.motion_detected[track_id]:
                self.motion_detected[track_id] = is_moving_now
        else:
            self.motion_detected[track_id] = is_moving_now
            
        return self.motion_detected[track_id]
    
    # =========================================
    # PREPROCESS
    # =========================================

    def preprocess_face(self, face_img):
        face = cv2.resize(face_img, (FACE_SIZE, FACE_SIZE))

        lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        face = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        kernel = np.array([[0, -1, 0], [-1, 5.0, -1], [0, -1, 0]])
        face = cv2.filter2D(face, -1, kernel)
        return face

    # =========================================
    # EMBEDDING
    # =========================================

    def get_embedding(self, face_img):
        try:
            face_processed = self.preprocess_face(face_img)
            rgb = cv2.cvtColor(face_processed, cv2.COLOR_BGR2RGB)
            
            embedding = DeepFace.represent(
                img_path=rgb,
                model_name=MODEL_NAME,
                model=FACE_RECOGNITION_MODEL,
                detector_backend="skip",
                enforce_detection=False,
                align=False,
                normalization="ArcFace"
            )[0]["embedding"]
            
            embedding = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(embedding)
            
            if norm == 0:
                return None
                
            embedding = embedding / norm
            return embedding
            
        except Exception as e:
            print("Embedding error:", e)
            return None

    # =========================================
    # COSINE
    # =========================================

    def compare(self, e1, e2):
        if e1 is None or e2 is None:
            return 0
        return float(np.dot(e1, e2))

    # =========================================
    # EMBEDDING THREAD
    # =========================================

    def embedding_worker(self):
        while True:
            try:
                track_id, face_img = self.embedding_queue.get()
                embedding = self.get_embedding(face_img)
                self.result_queue.put((track_id, embedding))
            except Exception as e:
                print("Thread error:", e)

    # =========================================
    # CLEANUP
    # =========================================

    def cleanup_tracks(self):
        current_time = time.time()
        expired = []
        
        for track_id, last_time in self.last_seen_time.items():
            if current_time - last_time > LOST_TRACK_TOLERANCE:
                expired.append(track_id)
        
        for track_id in expired:
            self.embedding_buffer.pop(track_id, None)
            self.stable_id.pop(track_id, None)
            self.verify_counter.pop(track_id, None)
            self.verify_start_time.pop(track_id, None)
            self.verified_identity.pop(track_id, None)
            self.verification_completed.pop(track_id, None)
            self.last_seen_time.pop(track_id, None)
            self.unknown_start_time.pop(track_id, None)
            self.unknown_extended_time.pop(track_id, None)
            self.unknown_alert_cooldown.pop(track_id, None)
            self.prev_position.pop(track_id, None)
            self.motion_detected.pop(track_id, None)

    # =========================================
    # PROCESS THREAD RESULTS
    # =========================================

    def process_results(self):
        while not self.result_queue.empty():
            try:
                track_id, embedding = self.result_queue.get_nowait()
                if embedding is not None:
                    self.pending_results[track_id] = embedding
            except:
                pass

    # =========================================
    # MATCH - MODO RAPIDO
    # =========================================

    def match_face(self, face_img, face_id, frame_counter, current_position):
        current_time = time.time()
        self.last_seen_time[face_id] = current_time
        
        self.process_results()
        
        # IDENTIDAD YA CONFIRMADA
        if face_id in self.stable_id:
            return self.stable_id[face_id]
        
        # DETECTAR MOVIMIENTO
        is_moving = self.is_moving(face_id, current_position, current_time) if MOTION_MODE else False
        
        if is_moving:
            sharpness_threshold = SHARPNESS_FILTER - 5
            min_face = MIN_FACE_SIZE - 5
        else:
            sharpness_threshold = SHARPNESS_FILTER
            min_face = MIN_FACE_SIZE
        
        # FILTROS DE CALIDAD
        if face_img.shape[0] < min_face or face_img.shape[1] < min_face:
            return None
        
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if sharpness < sharpness_threshold:
            return None
        
        brightness = np.mean(gray)
        if brightness < 25 or brightness > 235:
            return None
        
        # ENVIAR A THREAD
        if frame_counter % EMBEDDING_SKIP_FRAMES == 0:
            if self.embedding_queue.qsize() < 20:
                try:
                    self.embedding_queue.put_nowait((face_id, face_img.copy()))
                except:
                    pass
        
        if face_id not in self.pending_results:
            return None
        
        embedding = self.pending_results.pop(face_id)
        
        # BUFFER DE EMBEDDINGS
        if face_id not in self.embedding_buffer:
            self.embedding_buffer[face_id] = deque(maxlen=MAX_BUFFER)
        
        self.embedding_buffer[face_id].append(embedding)
        
        if len(self.embedding_buffer[face_id]) < 1:
            return None
        
        emb_stack = np.array(self.embedding_buffer[face_id])
        mean_emb = np.mean(emb_stack, axis=0)
        embedding = mean_emb / np.linalg.norm(mean_emb)
        
        # COMPARAR CON BASE DE DATOS
        scores = []
        
        for name, emb_list in self.known_embeddings.items():
            emb_list_relevant = emb_list[-50:] if len(emb_list) > 50 else emb_list
            
            similarities = [self.compare(embedding, e) for e in emb_list_relevant]
            max_score = np.max(similarities)
            
            top_k = min(3, len(similarities))
            top_similarities = sorted(similarities)[-top_k:]
            avg_top = np.mean(top_similarities)
            
            consistency = np.std(top_similarities) if len(top_similarities) > 1 else 0
            stability_penalty = min(consistency * 0.08, 0.03)
            
            final_score = max_score * 0.75 + avg_top * 0.25
            final_score -= stability_penalty
            scores.append((name, final_score))
        
        if not scores:
            return None
        
        scores.sort(key=lambda x: x[1], reverse=True)
        best_name, best_score = scores[0]
        second_score = scores[1][1] if len(scores) > 1 else 0
        
        score_gap = best_score - second_score
        dynamic_threshold = THRESHOLD
        dynamic_min_score = MIN_SCORE
        dynamic_ratio = RATIO_THRESHOLD
        
        if best_score < 0.70:
            dynamic_ratio += 0.02
        
        if frame_counter % 30 == 0 and best_score >= 0.60:
            user_prefix = f"U:{self.user_id[:8]}" if self.user_id else "local"
            print(f"[DEBUG] {user_prefix} ID:{face_id} - {best_name}={best_score:.3f} | Gap={score_gap:.3f}")
        
        if (best_score >= dynamic_threshold and 
            best_score >= dynamic_min_score and 
            score_gap >= dynamic_ratio):
            candidate = best_name
        else:
            candidate = None
        
        # LÓGICA DE VERIFICACIÓN
        if face_id not in self.verify_counter:
            self.verify_counter[face_id] = 0
            self.verify_start_time[face_id] = current_time
            self.verified_identity[face_id] = None
            self.verification_completed[face_id] = False
            user_prefix = f"U:{self.user_id[:8]}" if self.user_id else "local"
            print(f"[INICIO] {user_prefix} ID:{face_id} - Nueva persona")
        
        if self.verification_completed.get(face_id, False):
            return None
        
        time_elapsed = current_time - self.verify_start_time[face_id]
        
        if candidate is not None:
            if self.verified_identity[face_id] == candidate:
                self.verify_counter[face_id] += 1
                print(f"[✓] ID:{face_id} - {candidate}: {self.verify_counter[face_id]}/{VERIFY_REQUIRED}")
            else:
                self.verified_identity[face_id] = candidate
                self.verify_counter[face_id] = 1
                self.verify_start_time[face_id] = current_time
                print(f"[NUEVO] ID:{face_id} - {candidate}")
        
        if self.verify_counter[face_id] >= VERIFY_REQUIRED:
            self.stable_id[face_id] = self.verified_identity[face_id]
            self.verification_completed[face_id] = True
            print(f"\n✅ [CONFIRMADO] ID:{face_id} = {self.stable_id[face_id]} en {time_elapsed:.1f}s")
            return self.stable_id[face_id]
        
        if time_elapsed > VERIFY_WINDOW and self.verify_counter[face_id] < VERIFY_REQUIRED:
            if self.verify_counter[face_id] > 0:
                print(f"[⏱️] ID:{face_id} - Tiempo agotado ({self.verify_counter[face_id]}/{VERIFY_REQUIRED})")
            self.verify_counter[face_id] = 0
            self.verify_start_time[face_id] = current_time
            self.verified_identity[face_id] = None
        
        return None

    # =========================================
    # LOAD DB (Multi-usuario)
    # =========================================

    def load_database(self):
        user_name = f"usuario {self.user_id[:8]}..." if self.user_id else "local"
        print(f"\n📂 Cargando base de datos para {user_name}")
        self.known_embeddings = {}
        
        if not self.known_faces_dir.exists():
            print(f"   No hay rostros registrados aún")
            return
        
        for person_dir in self.known_faces_dir.iterdir():
            if not person_dir.is_dir():
                continue
            
            embeddings = []
            for img_file in person_dir.iterdir():
                if img_file.suffix.lower() not in ['.jpg', '.png', '.jpeg']:
                    continue
                
                img = cv2.imread(str(img_file))
                if img is None:
                    continue
                
                emb = self.get_embedding(img)
                if emb is not None:
                    embeddings.append(emb)
            
            if len(embeddings) > MAX_EMBEDDINGS:
                embeddings = embeddings[:MAX_EMBEDDINGS]
            
            if embeddings:
                self.known_embeddings[person_dir.name] = embeddings
                print(f"✅ {person_dir.name}: {len(embeddings)} embeddings")
        
        print(f"\n👤 {user_name}: {len(self.known_embeddings)} personas cargadas")
        print(f"⚡ MODO RÁPIDO: {VERIFY_REQUIRED} aciertos en {VERIFY_WINDOW}s")
        print(f"🎯 THRESHOLD: {THRESHOLD*100:.0f}% | MIN: {MIN_SCORE*100:.0f}%")
    
    # =========================================
    # REGISTRAR PERSONA (Multi-usuario)
    # =========================================
    
    def register_person(self, name: str, face_img=None):
        """Registra una nueva persona para este usuario"""
        folder = self.known_faces_dir / name.lower().replace(" ", "_")
        
        folder.mkdir(parents=True, exist_ok=True)
        
        if face_img is not None:
            filename = folder / f"{datetime.now().strftime('%H%M%S_%f')}.jpg"
            cv2.imwrite(str(filename), face_img)
            print(f"✅ Persona '{name}' registrada")
        
        self.load_database()
        return True
    
    # =========================================
    # ELIMINAR PERSONA
    # =========================================
    
    def delete_person(self, name: str):
        """Elimina una persona registrada"""
        folder = self.known_faces_dir / name.lower().replace(" ", "_")
        
        if folder.exists():
            shutil.rmtree(folder)
            self.load_database()
            print(f"🗑️ Persona '{name}' eliminada")
            return True
        return False
    
    # =========================================
    # OBTENER LISTA DE PERSONAS
    # =========================================
    
    def get_known_faces(self):
        """Retorna lista de personas registradas"""
        return list(self.known_embeddings.keys())

# =========================================
# REGISTRO (Mantener compatibilidad con modo local)
# =========================================

def register_person_local(name, cap, recognizer):
    """Función de registro original para modo local"""
    folder = recognizer.known_faces_dir / name.lower().replace(" ", "_")
    
    if folder.exists():
        shutil.rmtree(folder)
    
    folder.mkdir(parents=True)
    print(f"\n📸 Registrando a {name}")
    print("   Muévete lentamente para capturar diferentes ángulos")
    
    start = time.time()
    duration = 25
    count = 0
    last_capture = 0
    previous_embeddings = []
    min_time_between_captures = 0.15
    duplicate_embedding_threshold = 0.95
    
    while time.time() - start < duration:
        ret, frame = cap.read()
        if not ret:
            continue
        
        detection_frame = cv2.resize(frame, (960, 540))
        results = model(detection_frame, verbose=False, conf=0.45, imgsz=640, device=0)
        
        scale_x = frame.shape[1] / 960
        scale_y = frame.shape[0] / 540
        
        for r in results:
            for box in r.boxes.xyxy:
                x1, y1, x2, y2 = map(int, box)
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)
                
                padding = 40
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(frame.shape[1], x2 + padding)
                y2 = min(frame.shape[0], y2 + padding)
                
                face = frame[y1:y2, x1:x2]
                if face.size == 0:
                    continue
                
                if face.shape[0] < 100 or face.shape[1] < 100:
                    continue
                
                gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                if sharpness < 50:
                    continue
                
                now = time.time()
                if now - last_capture < min_time_between_captures:
                    continue

                emb = recognizer.get_embedding(face)
                if emb is not None and previous_embeddings:
                    sims = [recognizer.compare(emb, e) for e in previous_embeddings]
                    max_sim = max(sims) if sims else 0.0
                    if max_sim >= duplicate_embedding_threshold:
                        # Foto demasiado similar a una ya guardada
                        continue

                filename = folder / f"{datetime.now().strftime('%H%M%S_%f')}.jpg"
                cv2.imwrite(str(filename), face)
                if emb is not None:
                    previous_embeddings.append(emb)
                count += 1
                last_capture = now
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        cv2.putText(frame, f"{name} Fotos:{count}", (10, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        preview = cv2.resize(frame, (960, 540))
        cv2.imshow("Registro", preview)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    cv2.destroyAllWindows()
    print(f"✅ Registro completado: {count} fotos")
    recognizer.load_database()

# =========================================
# MAIN (Modo local - para pruebas)
# =========================================

def main():
    global MOTION_MODE
    
    print("\n" + "="*70)
    print("SISTEMA DE RECONOCIMIENTO FACIAL - MODO LOCAL")
    print("   (Para modo multi-usuario, usar api_server.py)")
    print("="*70 + "\n")
    
    recognizer = SimpleFaceRecognizer()  # Modo local (sin user_id)
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    frame_counter = 0
    fps_counter = 0
    fps = 0
    last_fps_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        detection_frame = cv2.resize(frame, (1280, 720))
        
        results = model.track(
            detection_frame,
            persist=True,
            verbose=False,
            conf=0.50,
            iou=0.75,
            tracker="bytetrack.yaml",
            imgsz=DETECTION_SIZE,
            device=0
        )
        
        scale_x = frame.shape[1] / 1280
        scale_y = frame.shape[0] / 720
        
        for r in results:
            if r.boxes.id is None:
                continue
            
            boxes = r.boxes.xyxy.cpu().numpy()
            ids = r.boxes.id.cpu().numpy().astype(int)
            
            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)
                
                padding = 25
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(frame.shape[1], x2 + padding)
                y2 = min(frame.shape[0], y2 + padding)
                
                face = frame[y1:y2, x1:x2]
                if face.size == 0:
                    continue
                
                current_position = ((x1 + x2) // 2, (y1 + y2) // 2)
                
                name = recognizer.match_face(face, track_id, frame_counter, current_position)
                current_time = time.time()
                
                if name:
                    recognizer.unknown_start_time.pop(track_id, None)
                    
                    is_moving = recognizer.motion_detected.get(track_id, False)
                    icon = "🏃" if is_moving else "✓"
                    label = f"{name} {icon}"
                    color = (0, 255, 0)
                else:
                    color = (0, 0, 255)
                    
                    if track_id not in recognizer.unknown_start_time:
                        recognizer.unknown_start_time[track_id] = current_time
                    
                    elapsed = current_time - recognizer.unknown_start_time.get(track_id, current_time)
                    
                    if track_id in recognizer.verify_counter and recognizer.verify_counter.get(track_id, 0) > 0:
                        label = f"VERIF... ({recognizer.verify_counter[track_id]}/{VERIFY_REQUIRED})"
                    else:
                        label = f"DESCONOCIDO ({elapsed:.0f}s)"
                    
                    if elapsed >= 10.0 and track_id not in recognizer.unknown_alert_cooldown:
                        recognizer.unknown_alert_cooldown[track_id] = current_time
                        print(f"\n🚨 [ALERTA] Persona NO reconocida ID:{track_id}")
                        saved_path = recognizer.unknown_logger.save_unknown_face(face, track_id, current_time, "no_reconocido")
                        if saved_path:
                            print(f"📸 Foto: {saved_path}")
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        recognizer.cleanup_tracks()
        
        # FPS
        fps_counter += 1
        if time.time() - last_fps_time >= 1.0:
            fps = fps_counter
            fps_counter = 0
            last_fps_time = time.time()
        
        # Mostrar info
        mode_status = "🏃 MOVIMIENTO" if MOTION_MODE else "🧍 ESTÁTICO"
        cv2.putText(frame, f"FPS: {fps} | {mode_status} | RAPIDO: {VERIFY_REQUIRED}/{VERIFY_WINDOW}s", 
                   (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        num_people = len(recognizer.stable_id)
        cv2.putText(frame, f"RECONOCIDOS: {num_people}", (20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        preview = cv2.resize(frame, (960, 540))
        cv2.imshow("MIRA - MODO LOCAL", preview)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        
        if key == ord('r'):
            name = input("Nombre: ")
            register_person_local(name, cap, recognizer)
        
        if key == ord('m'):
            MOTION_MODE = not MOTION_MODE
            status = "✅ ACTIVADO" if MOTION_MODE else "❌ DESACTIVADO"
            print(f"\n🎯 Modo movimiento {status}")
        
        frame_counter += 1
    
    cap.release()
    cv2.destroyAllWindows()

# =========================================
# START
# =========================================

if __name__ == "__main__":
    main()