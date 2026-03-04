import os
import re
from time import sleep
from flask import Flask, jsonify, request
import psycopg2
import redis

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
EMAIL_REGEX = re.compile(r"^.+@(gmail\.com|outlook\.com|hotmail\.com)$", re.IGNORECASE)
PASS_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{1,50}$")

def get_redis():
    return redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

def incr_visits():
    r = get_redis()
    return r.incr("visits")

def wait_for_db(max_retries=20):
    for _ in range(max_retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.close()
            return
        except Exception:
            sleep(1)
    raise RuntimeError("DB no respondio, esta muerta")


def create_users_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(50) NOT NULL,
            apellido VARCHAR(50) NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.get("/")
def home():
    return jsonify({
        "message": "Hola desde Flask en Docker Compose",
        "services": {
            "/health": "Verifica la salud de la aplicacion",
            "/visits": "Cuenta las visitas usando Redis",
            "GET /users": "Muestra todos los usuarios",
            "POST /users": "Crea usuario"
        }
    })


@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        now = cur.fetchone()[0]
        cur.close()
        conn.close()

        r = get_redis()
        pong = r.ping()

        return jsonify({
            "status": "ok",
            "db_time": str(now),
            "redis_ping": pong
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.get("/visits")
def visits():
    try:
        count = incr_visits()
        return jsonify({"visits": int(count)})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.post("/users")
def create_user():
    try:
        incr_visits()
    except Exception:
        pass
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not nombre or not apellido or not email or not password:
        return jsonify({"status": "error", "message": "Faltan campos: nombre, apellido, email, password"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"status": "error", "message": "Email invalido: solo gmail.com, outlook.com, hotmail.com"}), 400

    if not PASS_REGEX.match(password):
        return jsonify({"status": "error", "message": "Password invalida: max 50, debe tener mayuscula, minuscula y numero"}), 400
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (nombre, apellido, email, password) VALUES (%s, %s, %s, %s) RETURNING id;",
            (nombre, apellido, email, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "message": "Usuario creado",
            "id": user_id
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.get("/users")
def list_users():
    try:
        incr_visits()
    except Exception:
        pass
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, created_at FROM users ORDER BY id ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        users = []
        for r in rows:
            users.append({
                "id": r[0],
                "nombre": r[1],
                "apellido": r[2],
                "email": r[3],
                "created_at": str(r[4])
            })

        return jsonify({
            "status": "ok",
            "count": len(users),
            "users": users
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    wait_for_db()
    create_users_table()
    app.run(host="0.0.0.0", port=8000)