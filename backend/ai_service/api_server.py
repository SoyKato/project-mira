import os
import cv2
import uuid
import shutil
import asyncio
import threading
import queue
import time
import subprocess
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client
import uvicorn

# =========================================
# CONFIGURACIÓN
# =========================================
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

if os.name == 'nt':
    os.environ["OMP_NUM_THREADS"] = "8"
    os.environ["MKL_NUM_THREADS"] = "8"

import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices("GPU")
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print("✅ TensorFlow usando GPU")
    except RuntimeError as e:
        print(e)

cv2.setNumThreads(4)

from ultralytics import YOLO
from deepface import DeepFace

# =========================================
# MODELO DE EMBEDDINGS - FACENET512
# =========================================
MODEL_NAME = "Facenet512"

# =========================================
# DIRECTORIOS
# =========================================
BASE_DIR = Path(__file__).parent
USERS_DATA_DIR = BASE_DIR / "users_data"
USERS_DATA_DIR.mkdir(exist_ok=True)

# =========================================
# PARÁMETROS OPTIMIZADOS PARA FACENET512
# =========================================

THRESHOLD = 0.85 
MIN_SCORE = 0.82
RATIO_THRESHOLD = 0.05 

VERIFY_REQUIRED = 2
VERIFY_WINDOW = 4.0 

SHARPNESS_FILTER = 28 # 
MIN_FACE_SIZE = 80 
MOTION_SPEED_THRESHOLD = 12

MAX_EMBEDDINGS = 30 # 
MAX_BUFFER = 3 # 
EMBEDDING_SKIP_FRAMES = 3 # 

FACE_SIZE = 96 # 
DETECTION_SIZE = 640 

# Tracking
LOST_TRACK_TOLERANCE = 8.0 # 

# =========================================
# CONFIGURACIÓN FASTAPI
# =========================================
app = FastAPI(title="MIRA Face Recognition API", version="4.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/unknown_faces", StaticFiles(directory=str(USERS_DATA_DIR)), name="unknown_faces")

# =========================================
# SESIONES ACTIVAS
# =========================================
active_sessions: Dict[str, Dict] = {}
recognizers: Dict[str, 'SimpleFaceRecognizer'] = {}

# =========================================
# SUPABASE
# =========================================
SUPABASE_URL = "https://rifdbtcnyrwhkqardjxd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpZmRidGNueXJ3aGtxYXJkanhkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzE4NDMzMSwiZXhwIjoyMDg4NzYwMzMxfQ.bZkeBAsNy2YQzkkhzIhGStgzqFrahV_u_21H3cDl2BE"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "mira-images")

# =========================================
# CONFIGURACIÓN POSTGRESQL UBUNTU SERVER
# =========================================
import psycopg2
from psycopg2.extras import Json

# Configuración de conexión a Ubuntu Server
UBUNTU_DB_CONFIG = {
    "host": "192.168.0.159",
    "port": 5432,
    "dbname": "mira",
    "user": "mira_user",
    "password": "Mira2024Secure"
}

# =========================================
# ALMACENAMIENTO DE IMÁGENES EN UBUNTU (CON CLAVE SSH)
# =========================================
UBUNTU_IMAGE_SHARE_PATH = os.environ.get("UBUNTU_IMAGE_SHARE_PATH")
UBUNTU_SFTP_HOST = os.environ.get("UBUNTU_SFTP_HOST", "192.168.0.159")
UBUNTU_SFTP_PORT = int(os.environ.get("UBUNTU_SFTP_PORT", 22))
UBUNTU_SFTP_USER = os.environ.get("UBUNTU_SFTP_USER", "lck")
UBUNTU_SFTP_KEY_PATH = os.environ.get("UBUNTU_SFTP_KEY_PATH", os.path.expanduser("~/.ssh/id_rsa"))
UBUNTU_IMAGE_BASE_DIR = os.environ.get("UBUNTU_IMAGE_BASE_DIR", "/home/lck/mira_images")

PARAMIKO_AVAILABLE = False
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

# =========================================
# ESTADO DEL SERVIDOR UBUNTU (verificado una sola vez)
# =========================================
UBUNTU_SERVER_AVAILABLE = None

def check_ubuntu_server():
    """Verificar si el servidor Ubuntu está disponible (solo una vez al inicio)"""
    global UBUNTU_SERVER_AVAILABLE
    
    if UBUNTU_SERVER_AVAILABLE is not None:
        return UBUNTU_SERVER_AVAILABLE
    
    print("🔍 Verificando conexión con servidor Ubuntu...")
    
    # Verificar PostgreSQL
    pg_ok = False
    try:
        conn = psycopg2.connect(**UBUNTU_DB_CONFIG, connect_timeout=2)
        conn.close()
        pg_ok = True
    except:
        pass
    
    # Verificar SSH/SFTP
    ssh_ok = False
    if PARAMIKO_AVAILABLE and os.path.exists(UBUNTU_SFTP_KEY_PATH):
        try:
            transport = paramiko.Transport((UBUNTU_SFTP_HOST, UBUNTU_SFTP_PORT))
            transport.connect_timeout = 2
            key = paramiko.RSAKey.from_private_key_file(UBUNTU_SFTP_KEY_PATH)
            transport.connect(username=UBUNTU_SFTP_USER, pkey=key)
            transport.close()
            ssh_ok = True
        except:
            pass
    
    UBUNTU_SERVER_AVAILABLE = (pg_ok or ssh_ok)
    
    if UBUNTU_SERVER_AVAILABLE:
        print("✅ Servidor Ubuntu disponible - Backups ACTIVADOS")
    else:
        print("⚠️ Servidor Ubuntu NO disponible - Backups DESACTIVADOS (modo offline)")
    
    return UBUNTU_SERVER_AVAILABLE

def get_ubuntu_connection():
    """Obtener conexión a PostgreSQL (solo si servidor disponible)"""
    if not UBUNTU_SERVER_AVAILABLE:
        return None
    try:
        conn = psycopg2.connect(**UBUNTU_DB_CONFIG, connect_timeout=2)
        conn.autocommit = True
        return conn
    except Exception:
        return None

def replicate_to_ubuntu(table: str, data: dict):
    """Replicar datos (solo si servidor disponible)"""
    if not UBUNTU_SERVER_AVAILABLE:
        return False
    
    conn = get_ubuntu_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            cur.execute(query, list(data.values()))
            return True
    except Exception:
        return False
    finally:
        conn.close()

def update_ubuntu(table: str, data: dict, where_condition: str, where_params: tuple):
    """Actualizar datos (solo si servidor disponible)"""
    if not UBUNTU_SERVER_AVAILABLE:
        return False
    
    conn = get_ubuntu_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {where_condition}"
            params = list(data.values()) + list(where_params)
            cur.execute(query, params)
            return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_ubuntu(table: str, where_condition: str, where_params: tuple):
    """Eliminar datos (solo si servidor disponible)"""
    if not UBUNTU_SERVER_AVAILABLE:
        return False
    
    conn = get_ubuntu_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            query = f"DELETE FROM {table} WHERE {where_condition}"
            cur.execute(query, where_params)
            return True
    except Exception:
        return False
    finally:
        conn.close()

def copy_image_to_ubuntu(local_path: Path, relative_path: str) -> bool:
    """Copiar imagen (solo si servidor disponible)"""
    if not UBUNTU_SERVER_AVAILABLE:
        return False
    
    try:
        if not PARAMIKO_AVAILABLE:
            return False

        remote_relative = relative_path.lstrip("/")
        remote_path = f"{UBUNTU_IMAGE_BASE_DIR.rstrip('/')}/{remote_relative}"
        remote_dir = os.path.dirname(remote_path)

        transport = paramiko.Transport((UBUNTU_SFTP_HOST, UBUNTU_SFTP_PORT))
        transport.connect_timeout = 2
        
        if os.path.exists(UBUNTU_SFTP_KEY_PATH):
            key = paramiko.RSAKey.from_private_key_file(UBUNTU_SFTP_KEY_PATH)
            transport.connect(username=UBUNTU_SFTP_USER, pkey=key)
        else:
            return False

        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Crear directorio remoto si no existe
        remote_dir = remote_dir.replace("\\", "/")
        parts = [p for p in remote_dir.split("/") if p]
        path = ""
        for part in parts:
            path = f"{path}/{part}" if path else f"/{part}"
            try:
                sftp.stat(path)
            except:
                try:
                    sftp.mkdir(path)
                except:
                    pass
        
        sftp.put(str(local_path), remote_path)
        sftp.close()
        transport.close()
        return True
    except Exception:
        return False

def build_public_image_url(path: Path) -> str:
    relative_path = path.relative_to(USERS_DATA_DIR).as_posix()
    return f"/unknown_faces/{relative_path}"

def save_security_event(
    user_id: str,
    event_type: str,
    person_name: Optional[str],
    confidence: Optional[float],
    image_path: str
):
    event_type_mapping = {
        "unknown_face": "unknown_face",
        "known_face": "known_face",
        "motion_detected": "motion_detected"
    }
    pg_event_type = event_type_mapping.get(event_type, "unknown_face")
    
    # Guardar en Supabase
    try:
        supabase.table("security_events").insert([{
            "user_id": user_id,
            "event_type": event_type,
            "person_name": person_name,
            "confidence": confidence,
            "image_path": image_path,
            "timestamp": datetime.utcnow().isoformat(),
            "is_viewed": False
        }]).execute()
        print(f"✅ Evento guardado en Supabase")
    except Exception as e:
        import traceback
        print(f"❌ Error guardando evento de seguridad en Supabase:")
        traceback.print_exc()
    
    # Replicar en Ubuntu (solo si servidor disponible)
    if UBUNTU_SERVER_AVAILABLE:
        replicate_to_ubuntu("security_events", {
            "user_id": user_id,
            "event_type": pg_event_type,
            "person_name": person_name,
            "confidence": confidence,
            "image_path": image_path,
            "timestamp": datetime.utcnow(),
            "is_viewed": False
        })

# =========================================
# MODELO YOLO - YOLOv8m-face
# =========================================
DEVICE = "cuda" if len(gpus) > 0 else "cpu"
print(f"⚡ Usando dispositivo: {DEVICE}")
model_path = BASE_DIR / "face_yolov8m.pt"
model = YOLO(str(model_path)).to(DEVICE)

# =========================================
# MODELOS PYDANTIC
# =========================================
class FaceRecognitionResult(BaseModel):
    recognized: bool
    name: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    bbox: Optional[List[int]] = None
    track_id: Optional[int] = None
    candidate: Optional[str] = None
    top_score: Optional[float] = None
    second_score: Optional[float] = None
    score_gap: Optional[float] = None
    average_score: Optional[float] = None
    verify_count: Optional[int] = None
    verify_required: Optional[int] = None
    unknown_image_url: Optional[str] = None

class RecognitionResponse(BaseModel):
    recognized: bool
    name: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    bbox: Optional[List[int]] = None
    session_id: str
    results: Optional[List[FaceRecognitionResult]] = None

# =========================================
# RECOGNIZER
# =========================================

class SimpleFaceRecognizer:
    def __init__(self, user_id: str):
        self.user_id = user_id

        self.user_dir = USERS_DATA_DIR / user_id
        self.known_faces_dir = self.user_dir / "known_faces"
        self.unknown_faces_dir = self.user_dir / "unknown_faces"

        for d in [self.known_faces_dir, self.unknown_faces_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.known_embeddings: Dict[str, List[np.ndarray]] = {}
        self.embedding_buffer: Dict[int, deque] = {}
        self.load_database()

    def preprocess_face(self, face_img: np.ndarray) -> np.ndarray:
        face = cv2.resize(face_img, (FACE_SIZE, FACE_SIZE))

        lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        face = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        return np.ascontiguousarray(face, dtype=np.uint8)

    def get_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        try:
            face_processed = self.preprocess_face(face_img)
            rgb = cv2.cvtColor(face_processed, cv2.COLOR_BGR2RGB)

            embedding_obj = DeepFace.represent(
                img_path=rgb,
                model_name=MODEL_NAME,
                detector_backend="skip",
                enforce_detection=False,
                align=False,
                normalization="Facenet"
            )

            if not embedding_obj or len(embedding_obj) == 0:
                return None

            embedding = np.array(embedding_obj[0]["embedding"], dtype=np.float32)
            norm = np.linalg.norm(embedding)
            if norm == 0:
                return None

            return embedding / norm

        except Exception as e:
            print(f"⚠️ Error embedding: {e}")
            return None

    def compare(self, e1: np.ndarray, e2: np.ndarray) -> float:
        if e1 is None or e2 is None:
            return 0.0
        return float(np.dot(e1, e2))

    def check_face_quality(self, face_img: np.ndarray, is_moving: bool = False) -> bool:
        min_size = MIN_FACE_SIZE - 5 if is_moving else MIN_FACE_SIZE
        h, w = face_img.shape[:2]
        if h < min_size or w < min_size:
            return False

        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        if sharpness < SHARPNESS_FILTER:
            return False

        brightness = np.mean(gray)
        if brightness < 25 or brightness > 235:
            return False

        return True

    def load_database(self):
        print(f"\n📂 Cargando base de datos para usuario: {self.user_id[:8]}...")
        self.known_embeddings = {}

        if not self.known_faces_dir.exists():
            return

        for person_dir in self.known_faces_dir.iterdir():
            if not person_dir.is_dir():
                continue

            embeddings = []
            for img_file in list(person_dir.iterdir())[:MAX_EMBEDDINGS]:
                if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                    continue

                img = cv2.imread(str(img_file))
                if img is None:
                    continue

                emb = self.get_embedding(img)
                if emb is not None:
                    embeddings.append(emb)

            if embeddings:
                self.known_embeddings[person_dir.name] = embeddings
                print(f"✅ {person_dir.name}: {len(embeddings)} embeddings")

        print(f"👤 Total: {len(self.known_embeddings)} personas")

    def reload_database(self):
        self.load_database()

    def get_known_faces(self) -> List[str]:
        return list(self.known_embeddings.keys())

# =========================================
# FUNCIONES DE SESIÓN
# =========================================

def get_or_create_session(session_id: str, user_id: str) -> Dict:
    if session_id not in active_sessions:
        current_time = time.time()
        expired = [sid for sid, sess in active_sessions.items() 
                   if current_time - sess.get("last_activity", 0) > 30]
        for sid in expired:
            del active_sessions[sid]

        active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "embedding_buffer": {},
            "verify_counter": {},
            "verify_start_time": {},
            "verified_identity": {},
            "verification_completed": {},
            "stable_id": {},
            "candidate_scores": {},
            "last_seen_time": {},
            "pending_results": {},
            "prev_position": {},
            "motion_detected": {},
            "unknown_captured": {},
            "unknown_urls": {},
            "last_embedding": {},
            "last_embedding_frame": {},
            "last_activity": time.time(),
            "frame_counter": 0
        }
        print(f"📱 Nueva sesión creada: {session_id[:8]}...")
    
    active_sessions[session_id]["last_activity"] = time.time()
    active_sessions[session_id]["frame_counter"] += 1
    
    return active_sessions[session_id]

def is_moving(session: Dict, track_id: int, current_position: Tuple[int, int]) -> bool:
    if track_id not in session["prev_position"]:
        session["prev_position"][track_id] = current_position
        session["motion_detected"][track_id] = False
        return False
    
    prev_x, prev_y = session["prev_position"][track_id]
    curr_x, curr_y = current_position
    distance = np.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
    session["prev_position"][track_id] = current_position
    
    is_moving_now = distance > MOTION_SPEED_THRESHOLD
    session["motion_detected"][track_id] = is_moving_now
    return is_moving_now

def save_unknown_face(user_id: str, session_id: str, track_id: int, face_img: np.ndarray) -> str:
    unknown_dir = USERS_DATA_DIR / user_id / "unknown_faces"
    unknown_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%d_%m_%y_%H_%M_%S")
    filename = f"unknown_{timestamp}.jpg"
    file_path = unknown_dir / filename

    success, buf = cv2.imencode('.jpg', face_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    public_url = None
    if success:
        file_path.write_bytes(buf.tobytes())
        public_url = build_public_image_url(file_path)
        
        # Backup a Ubuntu (solo si servidor disponible)
        copy_image_to_ubuntu(file_path, file_path.relative_to(USERS_DATA_DIR).as_posix())
        
        save_security_event(user_id, "unknown_face", None, None, public_url)
        
        try:
            supabase.table("unknown_faces_history").insert([{
                "user_id": user_id,
                "face_image_path": public_url,
                "confidence": None,
                "timestamp": datetime.utcnow().isoformat(),
                "is_reviewed": False
            }]).execute()
            print(f"✅ Cara desconocida guardada en historial (Supabase): {filename}")
        except Exception as e:
            import traceback
            print(f"⚠️ Error guardando en unknown_faces_history (Supabase):")
            traceback.print_exc()
        
        # Replicar en Ubuntu (solo si servidor disponible)
        if UBUNTU_SERVER_AVAILABLE:
            replicate_to_ubuntu("unknown_faces_history", {
                "user_id": user_id,
                "face_image_path": public_url,
                "confidence": None,
                "timestamp": datetime.utcnow(),
                "is_reviewed": False
            })

    return public_url or f"/unknown_faces/{user_id}/unknown_faces/{filename}"

def match_face_in_session(
    session: Dict,
    recognizer: SimpleFaceRecognizer,
    face_img: np.ndarray,
    track_id: int,
    current_position: Tuple[int, int],
    is_moving: bool
) -> Dict:
    current_time = time.time()
    session["last_seen_time"][track_id] = current_time

    if not recognizer.check_face_quality(face_img, is_moving):
        return {"name": None, "recognized": False, "reason": "low_quality"}

    use_cached_embedding = False
    cached_frame = session["last_embedding_frame"].get(track_id, -EMBEDDING_SKIP_FRAMES)
    if session["frame_counter"] - cached_frame < EMBEDDING_SKIP_FRAMES:
        use_cached_embedding = track_id in session["last_embedding"]

    if use_cached_embedding:
        embedding = session["last_embedding"][track_id]
    else:
        embedding = recognizer.get_embedding(face_img)
        if embedding is not None:
            session["last_embedding"][track_id] = embedding
            session["last_embedding_frame"][track_id] = session["frame_counter"]

    if embedding is None:
        return {"name": None, "recognized": False, "reason": "no_embedding"}

    if track_id in session["stable_id"]:
        stable_name = session["stable_id"][track_id]
        stable_embeddings = recognizer.known_embeddings.get(stable_name, [])
        if stable_embeddings:
            similarities = [recognizer.compare(embedding, e) for e in stable_embeddings[-50:]]
            if similarities:
                return {
                    "name": stable_name,
                    "recognized": True,
                    "confidence": float(np.max(similarities)),
                    "reason": "stable_match"
                }
        else:
            return {
                "name": stable_name,
                "recognized": True,
                "confidence": 0.90,
                "reason": "stable_match"
            }

    if track_id not in session["embedding_buffer"]:
        session["embedding_buffer"][track_id] = deque(maxlen=MAX_BUFFER)
    session["embedding_buffer"][track_id].append(embedding)

    emb_stack = np.array(session["embedding_buffer"][track_id])
    if emb_stack.size == 0:
        return {"name": None, "recognized": False, "reason": "empty_buffer"}

    embedding = emb_stack[-1]
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return {"name": None, "recognized": False, "reason": "invalid_embedding"}

    embedding = embedding / norm

    scores = []
    for name, emb_list in recognizer.known_embeddings.items():
        if len(emb_list) == 0:
            continue

        emb_list_relevant = emb_list[-50:]
        similarities = [recognizer.compare(embedding, e) for e in emb_list_relevant]
        if not similarities:
            continue

        max_score = np.max(similarities)
        top_k = min(10, len(similarities))
        top_similarities = sorted(similarities)[-top_k:]
        avg_top = np.mean(top_similarities)
        final_score = float((max_score * 0.65) + (avg_top * 0.35))

        scores.append({
            "name": name,
            "score": float(final_score),
            "max_score": float(max_score),
            "avg_top": float(avg_top)
        })

    if not scores:
        return {"name": None, "recognized": False, "reason": "no_known_faces"}

    scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    best = scores[0]
    best_name = best["name"]
    best_score = best["score"]
    second_score = scores[1]["score"] if len(scores) > 1 else 0.0
    score_gap = best_score - second_score

    candidate = None
    if (best_score >= THRESHOLD and best_score >= MIN_SCORE and score_gap >= RATIO_THRESHOLD):
        candidate = best_name

    if track_id not in session["verify_counter"]:
        session["verify_counter"][track_id] = 0
        session["verify_start_time"][track_id] = current_time
        session["verified_identity"][track_id] = None
        session["verification_completed"][track_id] = False
        session["unknown_captured"][track_id] = False
        session["unknown_urls"][track_id] = None
        print(f"[INICIO] ID:{track_id} - Nueva persona")

    time_elapsed = current_time - session["verify_start_time"][track_id]

    if session["verification_completed"].get(track_id, False):
        return {
            "name": session["stable_id"].get(track_id),
            "recognized": True,
            "confidence": float(best_score),
            "reason": "confirmed",
            "verify_count": VERIFY_REQUIRED,
            "verify_required": VERIFY_REQUIRED
        }

    if candidate is not None:
        if session["verified_identity"][track_id] == candidate:
            session["verify_counter"][track_id] += 1
            print(f"[✓] ID:{track_id} - {candidate}: {session['verify_counter'][track_id]}/{VERIFY_REQUIRED} (score={best_score:.3f})")
        else:
            session["verified_identity"][track_id] = candidate
            session["verify_start_time"][track_id] = current_time
            session["verify_counter"][track_id] = 1
            print(f"[NUEVO] ID:{track_id} - {candidate} (score={best_score:.3f})")
    else:
        if session["verify_counter"][track_id] > 0:
            print(f"[RESET] ID:{track_id} - Verificación reiniciada")
        session["verify_counter"][track_id] = 0
        session["verified_identity"][track_id] = None

    if session["verify_counter"][track_id] >= VERIFY_REQUIRED:
        session["stable_id"][track_id] = session["verified_identity"][track_id]
        session["verification_completed"][track_id] = True
        print(f"\n✅ [CONFIRMADO] ID:{track_id} = {session['stable_id'][track_id]} en {time_elapsed:.1f}s")
        return {
            "name": session['stable_id'][track_id],
            "recognized": True,
            "confidence": float(best_score),
            "reason": "confirmed",
            "verify_count": session["verify_counter"][track_id],
            "verify_required": VERIFY_REQUIRED
        }

    if time_elapsed > VERIFY_WINDOW and session["verify_counter"][track_id] < VERIFY_REQUIRED:
        if session["verify_counter"][track_id] > 0:
            print(f"[⏱️] ID:{track_id} - Tiempo agotado ({session['verify_counter'][track_id]}/{VERIFY_REQUIRED})")
        if not session["unknown_captured"].get(track_id, False):
            unknown_url = save_unknown_face(recognizer.user_id, session["session_id"], track_id, face_img)
            session["unknown_captured"][track_id] = True
            session["unknown_urls"][track_id] = unknown_url
            print(f"[❓] ID:{track_id} - Desconocido capturado: {unknown_url}")
        else:
            unknown_url = session["unknown_urls"].get(track_id)

        session["verify_counter"][track_id] = 0
        session["verify_start_time"][track_id] = current_time
        session["verified_identity"][track_id] = None

        return {
            "name": None,
            "recognized": False,
            "reason": "unknown_face",
            "verify_count": session["verify_counter"][track_id],
            "verify_required": VERIFY_REQUIRED,
            "unknown_image_url": unknown_url
        }

    return {
        "name": None,
        "recognized": False,
        "reason": "verifying",
        "verify_count": session["verify_counter"][track_id],
        "verify_required": VERIFY_REQUIRED
    }

def cleanup_session_old_tracks(session: Dict):
    current_time = time.time()
    expired = []
    
    for track_id, last_time in session["last_seen_time"].items():
        if current_time - last_time > LOST_TRACK_TOLERANCE:
            expired.append(track_id)
    
    for track_id in expired:
        session["embedding_buffer"].pop(track_id, None)
        session["stable_id"].pop(track_id, None)
        session["verify_counter"].pop(track_id, None)
        session["verify_start_time"].pop(track_id, None)
        session["verified_identity"].pop(track_id, None)
        session["verification_completed"].pop(track_id, None)
        session["unknown_captured"].pop(track_id, None)
        session["unknown_urls"].pop(track_id, None)
        session["last_embedding"].pop(track_id, None)
        session["last_embedding_frame"].pop(track_id, None)
        session["last_seen_time"].pop(track_id, None)
        session["prev_position"].pop(track_id, None)
        session["motion_detected"].pop(track_id, None)

def sanitize_folder_name(name: str) -> str:
    cleaned = ''.join(
        c if c.isalnum() or c in (' ', '_', '-') else '_'
        for c in name.strip()
    )
    return cleaned.replace(' ', '_').lower()

# =========================================
# DETECTOR DE ROSTROS CON TRACKING
# =========================================

def detect_faces_with_tracking(image: np.ndarray) -> List[Dict]:
    detection_frame = cv2.resize(image, (1280, 720))
    
    results = model.track(
        detection_frame,
        persist=True,
        verbose=False,
        conf=0.35,
        iou=0.55,
        tracker="bytetrack.yaml",
        imgsz=DETECTION_SIZE,
        device=DEVICE
    )
    
    scale_x = image.shape[1] / 1280
    scale_y = image.shape[0] / 720
    
    faces = []
    
    for r in results:
        if r.boxes is None or r.boxes.id is None:
            continue
        
        boxes = r.boxes.xyxy.cpu().numpy()
        track_ids = r.boxes.id.cpu().numpy().astype(int)
        
        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = map(int, box)
            
            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)
            
            padding = 25
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(image.shape[1], x2 + padding)
            y2 = min(image.shape[0], y2 + padding)
            
            face = image[y1:y2, x1:x2]
            
            if face.size == 0:
                continue
            
            if face.shape[0] < MIN_FACE_SIZE or face.shape[1] < MIN_FACE_SIZE:
                continue
            
            faces.append({
                "bbox": [x1, y1, x2, y2],
                "face_img": face,
                "track_id": int(track_id)
            })
    
    return faces

# =========================================
# DETECTOR DE ROSTROS PARA REGISTRO
# =========================================

def detect_and_crop_faces(image: np.ndarray) -> List[np.ndarray]:
    detection_frame = cv2.resize(image, (640, 360))
    
    results = model(
        detection_frame,
        verbose=False,
        conf=0.45,
        imgsz=640,
        device=DEVICE
    )
    
    scale_x = image.shape[1] / 640
    scale_y = image.shape[0] / 360
    
    faces = []
    
    for r in results:
        if r.boxes is None:
            continue
        
        boxes = r.boxes.xyxy.cpu().numpy()
        
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            
            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)
            
            padding = 20
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(image.shape[1], x2 + padding)
            y2 = min(image.shape[0], y2 + padding)
            
            face = image[y1:y2, x1:x2]
            
            if face.size == 0:
                continue
            
            if face.shape[0] < MIN_FACE_SIZE or face.shape[1] < MIN_FACE_SIZE:
                continue
            
            faces.append(face)
    
    return faces

# =========================================
# ENDPOINTS
# =========================================

@app.get("/")
async def root():
    return {
        "message": "MIRA Face Recognition API",
        "version": "4.1.0 - FACENET512 OPTIMIZADO",
        "features": ["Tracking con YOLO", "Verificación multi-frame", "Buffer de embeddings"],
        "thresholds": {
            "THRESHOLD": THRESHOLD,
            "MIN_SCORE": MIN_SCORE,
            "RATIO_THRESHOLD": RATIO_THRESHOLD,
            "VERIFY_REQUIRED": VERIFY_REQUIRED,
            "VERIFY_WINDOW": VERIFY_WINDOW,
            "MIN_FACE_SIZE": MIN_FACE_SIZE,
            "SHARPNESS_FILTER": SHARPNESS_FILTER
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "active_users": len(recognizers),
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/recognize")
async def recognize_face(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(400, "Imagen inválida")
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    faces = detect_faces_with_tracking(img)
    
    if len(faces) == 0:
        return RecognitionResponse(
            recognized=False,
            reason="no_face_detected",
            session_id=session_id,
            results=[]
        )
    
    if user_id not in recognizers:
        recognizers[user_id] = SimpleFaceRecognizer(user_id)
    
    recognizer = recognizers[user_id]
    session = get_or_create_session(session_id, user_id)
    
    all_results = []
    any_recognized = False
    
    for face_data in faces:
        track_id = face_data["track_id"]
        bbox = face_data["bbox"]
        face_img = face_data["face_img"]
        
        center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
        moving = is_moving(session, track_id, center)
        
        match_info = match_face_in_session(session, recognizer, face_img, track_id, center, moving)
        name = match_info.get("name")
        recognized = match_info.get("recognized", False)
        reason = match_info.get("reason")
        verify_count = match_info.get("verify_count", 0)
        verify_required = match_info.get("verify_required", VERIFY_REQUIRED)
        
        if recognized:
            any_recognized = True
        
        all_results.append({
            "recognized": recognized,
            "name": name,
            "confidence": 0.85 if recognized else 0.0,
            "reason": reason if reason is not None else ("verifying" if session["verify_counter"].get(track_id, 0) > 0 else "unknown_face"),
            "bbox": bbox,
            "track_id": track_id,
            "verify_count": verify_count,
            "verify_required": verify_required,
            "unknown_image_url": match_info.get("unknown_image_url")
        })
    
    cleanup_session_old_tracks(session)
    
    return RecognitionResponse(
        recognized=any_recognized,
        session_id=session_id,
        results=all_results
    )

@app.get("/api/known-faces/{user_id}")
async def get_known_faces(user_id: str):
    if user_id not in recognizers:
        recognizers[user_id] = SimpleFaceRecognizer(user_id)

    recognizer = recognizers[user_id]
    faces = recognizer.get_known_faces()

    display_map = {}
    try:
        response = supabase.table("known_faces").select("name,notes").eq("user_id", user_id).execute()
        if response and response.data:
            for item in response.data:
                name_key = item.get("name")
                notes = item.get("notes", "")
                display_map[name_key] = name_key
    except Exception as e:
        import traceback
        print(f"⚠️ Error cargando nombres desde Supabase:")
        traceback.print_exc()

    usuarios = [
        {
            "id": i,
            "name": name,
            "nombre": display_map.get(name, name)
        }
        for i, name in enumerate(faces)
    ]

    return {
        "user_id": user_id,
        "faces": usuarios,
        "total": len(usuarios)
    }

@app.get("/api/unknown-faces-history/{user_id}")
async def get_unknown_faces_history(user_id: str, limit: int = 50):
    try:
        response = supabase.table("unknown_faces_history").select(
            "id,face_image_path,confidence,timestamp,is_reviewed"
        ).eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute()
        
        if response and response.data:
            return {
                "user_id": user_id,
                "unknown_faces": response.data,
                "total": len(response.data)
            }
        else:
            return {
                "user_id": user_id,
                "unknown_faces": [],
                "total": 0
            }
    except Exception as e:
        import traceback
        print(f"❌ Error recuperando historial de caras desconocidas:")
        traceback.print_exc()
        raise HTTPException(500, "Error recuperando historial")

@app.put("/api/mark-reviewed/{history_id}")
async def mark_as_reviewed(history_id: int):
    try:
        supabase.table("unknown_faces_history").update(
            {"is_reviewed": True}
        ).eq("id", history_id).execute()
        
        update_ubuntu("unknown_faces_history", 
                     {"is_reviewed": True}, 
                     "id = %s", 
                     (history_id,))
        
        return {"success": True, "message": "Marcado como revisado"}
    except Exception as e:
        import traceback
        print(f"❌ Error marcando como revisado:")
        traceback.print_exc()
        raise HTTPException(500, "Error marcando como revisado")

@app.post("/api/register/{user_id}")
async def register_person(
    user_id: str,
    name: str = Form(...),
    files: List[UploadFile] = File(...)
):
    print(f"\n{'='*60}")
    print(f"📸 REGISTRO INICIADO: {name}")
    print(f"📦 Fotos recibidas: {len(files)}")
    print(f"{'='*60}")
    
    try:
        user_check = supabase.table("users").select("id").eq("id", user_id).execute()
        if not user_check.data or len(user_check.data) == 0:
            print(f"⚠️ Usuario no encontrado en Supabase. Creando automáticamente: {user_id}")
            supabase.table("users").insert([{
                "id": user_id,
                "email": f"user_{user_id[:8]}@mira.local",
                "nombre": "Usuario MIRA",
                "password_hash": "test_hash"
            }]).execute()
            print(f"✅ Usuario creado en Supabase")
        
        # Crear usuario en Ubuntu solo si servidor disponible
        if UBUNTU_SERVER_AVAILABLE:
            ubuntu_conn = get_ubuntu_connection()
            if ubuntu_conn:
                try:
                    with ubuntu_conn.cursor() as cur:
                        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                        user_exists = cur.fetchone()
                        
                        if not user_exists:
                            cur.execute("""
                                INSERT INTO users (id, email, nombre, password_hash, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (user_id, f"user_{user_id[:8]}@mira.local", "Usuario MIRA", "test_hash", datetime.utcnow()))
                            print(f"✅ Usuario creado en Ubuntu PostgreSQL")
                        else:
                            print(f"✅ Usuario ya existe en Ubuntu PostgreSQL")
                except Exception:
                    pass
                finally:
                    ubuntu_conn.close()
                    
    except Exception as e:
        import traceback
        print(f"❌ Error verificando/creando usuario:")
        traceback.print_exc()
        raise HTTPException(500, "Error verificando autenticación del usuario")
    
    if not name or not name.strip():
        raise HTTPException(400, "El nombre de la persona es obligatorio")
    
    if not files:
        raise HTTPException(400, "Se requieren imágenes para registrar la persona")
    
    if user_id not in recognizers:
        recognizers[user_id] = SimpleFaceRecognizer(user_id)
    
    recognizer = recognizers[user_id]
    folder_name = sanitize_folder_name(name)
    person_folder = recognizer.known_faces_dir / folder_name
    
    if person_folder.exists():
        shutil.rmtree(person_folder)
    person_folder.mkdir(parents=True, exist_ok=True)
    
    saved_count = 0
    all_embeddings = []
    face_records = []
    
    for i, upload in enumerate(files):
        try:
            contents = await upload.read()
            image_array = np.frombuffer(contents, np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue
            
            faces = detect_and_crop_faces(frame)
            
            if len(faces) == 0:
                print(f"   ⚠️ Frame {i+1} sin detección - reintentando con fallback")
                small = cv2.resize(frame, (320, 320))
                faces = detect_and_crop_faces(small)
            
            if len(faces) == 0:
                print(f"   ⚠️ Foto {i+1}: No se detectó rostro")
                continue
            
            for j, face_img in enumerate(faces):
                if not recognizer.check_face_quality(face_img):
                    print(f"   ⚠️ Foto {i+1}: calidad insuficiente")
                    continue
                
                embedding = recognizer.get_embedding(face_img)
                
                if embedding is None:
                    continue
                
                is_duplicate = False
                for existing_emb in all_embeddings:
                    similarity = recognizer.compare(embedding, existing_emb)
                    if similarity > 0.998:
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    print(f"   ⚠️ Foto {i+1}: rostro duplicado (ignorado)")
                    continue
                
                filename = person_folder / f"{saved_count:04d}.jpg"
                cv2.imwrite(str(filename), face_img)
                
                # Backup a Ubuntu (solo si servidor disponible)
                copy_image_to_ubuntu(filename, filename.relative_to(USERS_DATA_DIR).as_posix())
                
                saved_count += 1
                all_embeddings.append(embedding)
                image_url = build_public_image_url(filename)
                face_records.append({
                    "user_id": user_id,
                    "face_id": None,
                    "embedding_vector": embedding.tolist(),
                    "image_path": image_url,
                    "created_at": datetime.utcnow().isoformat()
                })
                
                if saved_count % 10 == 0:
                    print(f"   📸 {saved_count} rostros guardados")
                
                if saved_count >= 50:
                    print(f"   📸 Límite de 50 fotos alcanzado")
                    break
            
            if saved_count >= 50:
                break
                
        except Exception as e:
            print(f"   ❌ Error en foto {i+1}: {e}")
            continue
    
    print(f"\n📊 RESULTADO: {saved_count} rostros guardados de {len(files)} fotos")
    
    if saved_count == 0:
        raise HTTPException(400, "No se pudo guardar ningún rostro válido")
    
    known_face_id = None
    try:
        supabase.table("known_faces").delete().eq("user_id", user_id).eq("name", folder_name).execute()
        
        delete_ubuntu("known_faces", "user_id = %s AND name = %s", (user_id, folder_name))
        
        response = supabase.table("known_faces").insert([{
            "user_id": user_id,
            "name": folder_name,
            "notes": f"Nombre real: {name} | Fotos: {saved_count}",
            "created_at": datetime.utcnow().isoformat()
        }]).select("id").execute()
        
        if response and response.data and len(response.data) > 0:
            known_face_id = response.data[0].get("id")
            print(f"✅ Registro en Supabase completado (ID: {known_face_id})")
            
            replicate_to_ubuntu("known_faces", {
                "user_id": user_id,
                "name": folder_name,
                "notes": f"Nombre real: {name} | Fotos: {saved_count}",
                "created_at": datetime.utcnow()
            })
        else:
            print(f"⚠️ No se obtuvo ID del registro en Supabase")
    except Exception as e:
        import traceback
        print(f"❌ Error en Supabase:")
        traceback.print_exc()

    if face_records:
        if known_face_id is not None:
            for record in face_records:
                record["face_id"] = known_face_id
        try:
            supabase.table("face_embeddings").insert(face_records).execute()
            print(f"✅ {len(face_records)} embeddings registrados en face_embeddings")
            
            if UBUNTU_SERVER_AVAILABLE:
                success_count = 0
                for record in face_records:
                    result = replicate_to_ubuntu("face_embeddings", {
                        "user_id": record["user_id"],
                        "face_id": record["face_id"],
                        "embedding_vector": Json(record["embedding_vector"]),
                        "image_path": record["image_path"],
                        "created_at": datetime.utcnow()
                    })
                    if result:
                        success_count += 1
                
                if success_count > 0:
                    print(f"✅ {success_count}/{len(face_records)} embeddings replicados en Ubuntu")
            
        except Exception as e:
            import traceback
            print("❌ Error guardando embeddings en Supabase:")
            traceback.print_exc()

    recognizer.reload_database()
    
    print(f"\n{'='*60}")
    print(f"✅ REGISTRO COMPLETADO: {saved_count} rostros de calidad")
    print(f"{'='*60}\n")
    
    return {
        "success": True,
        "images_saved": saved_count,
        "message": f"Persona '{name}' registrada con {saved_count} rostros"
    }

@app.delete("/api/delete-person/{user_id}/{name}")
async def delete_person(user_id: str, name: str):
    if user_id not in recognizers:
        recognizers[user_id] = SimpleFaceRecognizer(user_id)
    
    recognizer = recognizers[user_id]
    folder_name = sanitize_folder_name(name)
    folder = recognizer.known_faces_dir / folder_name
    
    if folder.exists():
        shutil.rmtree(folder)
        recognizer.reload_database()
        
        try:
            supabase.table("known_faces").delete().eq("user_id", user_id).eq("name", folder_name).execute()
            
            delete_ubuntu("known_faces", "user_id = %s AND name = %s", (user_id, folder_name))
            
        except Exception as e:
            import traceback
            print(f"⚠️ Error eliminando de Supabase:")
            traceback.print_exc()
        
        return {"success": True, "message": f"Persona '{name}' eliminada"}
    
    raise HTTPException(404, f"Persona '{name}' no encontrada")

# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 MIRA API SERVER v4.1 - FACENET512 OPTIMIZADO")
    print("="*70)
    
    # Verificar servidor Ubuntu UNA SOLA VEZ al iniciar
    check_ubuntu_server()
    
    print("✨ CAMBIOS CRÍTICOS IMPLEMENTADOS:")
    print(f"   1. ✅ THRESHOLD: {THRESHOLD}")
    print(f"   2. ✅ MIN_SCORE: {MIN_SCORE}")
    print(f"   3. ✅ RATIO_THRESHOLD: {RATIO_THRESHOLD}")
    print(f"   4. ✅ VERIFY_REQUIRED: {VERIFY_REQUIRED}")
    print(f"   5. ✅ SHARPNESS_FILTER: {SHARPNESS_FILTER}")
    print(f"   6. ✅ MIN_FACE_SIZE: {MIN_FACE_SIZE}")
    print("   7. ✅ Detector: conf=0.50, iou=0.75")
    print("   8. ✅ Registro: conf=0.45, imgsz=640")
    print("="*70)
    print(f"📁 Directorio: {Path(__file__).parent}")
    print(f"🌐 API: http://localhost:8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")