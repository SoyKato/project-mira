import psycopg2
import uuid
from datetime import datetime

print("="*60)
print("🔌 PROBANDO CONEXIÓN A POSTGRESQL UBUNTU")
print("="*60)

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host="192.168.0.159",
        port=5432,
        dbname="mira",
        user="mira_user",
        password="Mira2024Secure",
        connect_timeout=5
    )
    
    print("\n✅ ¡Conexión exitosa a PostgreSQL en Ubuntu!")
    
    cur = conn.cursor()
    
    # Obtener información de la conexión
    cur.execute("SELECT current_user, current_database();")
    user, db = cur.fetchone()
    print(f"📊 Conectado como: {user}")
    print(f"📚 Base de datos: {db}")
    
    # Listar tablas
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    print(f"\n📋 Tablas disponibles ({len(tables)}):")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Generar UUID para la prueba
    test_uuid = str(uuid.uuid4())
    print(f"\n🔑 UUID de prueba: {test_uuid}")
    
    # Insertar un usuario de prueba
    cur.execute("""
        INSERT INTO users (id, email, nombre, password_hash, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        RETURNING id;
    """, (test_uuid, "test@mira.com", "Usuario Prueba", "test_hash_123", datetime.now()))
    
    if cur.rowcount > 0:
        print(f"✅ Usuario de prueba insertado correctamente")
        
        # Insertar una cara conocida
        cur.execute("""
            INSERT INTO known_faces (user_id, name, notes, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (test_uuid, "test_person", "Cara de prueba", datetime.now()))
        
        face_id = cur.fetchone()[0]
        print(f"✅ Cara conocida creada (ID: {face_id})")
        
        # Insertar un embedding
        cur.execute("""
            INSERT INTO face_embeddings (user_id, face_id, embedding_vector, image_path, created_at)
            VALUES (%s, %s, %s, %s, %s);
        """, (test_uuid, face_id, '[0.1, 0.2, 0.3]', '/test/path.jpg', datetime.now()))
        print(f"✅ Embedding creado")
        
        # Insertar evento de seguridad con los tipos correctos
        event_types = ["known_face", "unknown_face", "motion_detected"]
        
        for event_type in event_types:
            cur.execute("""
                INSERT INTO security_events (user_id, event_type, person_name, confidence, image_path, timestamp, is_viewed)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (test_uuid, event_type, "test_person", 0.95, "/test/event.jpg", datetime.now(), False))
            print(f"✅ Evento '{event_type}' creado correctamente")
        
        # Insertar cara desconocida
        cur.execute("""
            INSERT INTO unknown_faces_history (user_id, face_image_path, confidence, timestamp, is_reviewed)
            VALUES (%s, %s, %s, %s, %s);
        """, (test_uuid, "/test/unknown.jpg", None, datetime.now(), False))
        print(f"✅ Cara desconocida registrada")
        
        # Limpiar datos de prueba
        cur.execute("DELETE FROM face_embeddings WHERE user_id = %s", (test_uuid,))
        cur.execute("DELETE FROM security_events WHERE user_id = %s", (test_uuid,))
        cur.execute("DELETE FROM unknown_faces_history WHERE user_id = %s", (test_uuid,))
        cur.execute("DELETE FROM known_faces WHERE user_id = %s", (test_uuid,))
        cur.execute("DELETE FROM users WHERE id = %s", (test_uuid,))
        print(f"\n✅ Datos de prueba eliminados correctamente")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("🌐 PostgreSQL en Ubuntu está listo para MIRA")
    print("="*60)
    
except psycopg2.OperationalError as e:
    print(f"\n❌ Error de conexión: {e}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona Enter para salir...")