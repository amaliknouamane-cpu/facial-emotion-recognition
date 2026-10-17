import base64
import sqlite3
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from flask_cors import CORS
except Exception:
    def CORS(app):
        @app.after_request
        def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            return response

        return app

try:
    import cv2
except Exception:
    cv2 = None


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "model.pth"
DB_PATH = ROOT_DIR / "users.db"
AHEGAO_DATASET_DIR = Path.home() / "Desktop" / "data" / "New folder" / "facial_emotion_dataset" / "dataset" / "Ahegao"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
sys.path.insert(0, str(ROOT_DIR))

from model_loader import EmotionPredictor

app = Flask(__name__)
CORS(app)

predictor = None


def get_predictor():
    global predictor
    if predictor is None:
        predictor = EmotionPredictor(MODEL_PATH)
    return predictor


def predictor_status(current_predictor):
    return {
        "ready": current_predictor.ready,
        "model_path": str(current_predictor.model_path),
        "model_name": current_predictor.model_name,
        "architecture": current_predictor.architecture,
        "message": "Modele charge" if current_predictor.ready else current_predictor.last_error,
        "labels": current_predictor.display_labels(),
    }


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS emotion_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                source_label TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def normalize_dataset_label(label):
    clean_label = (label or "").strip().lower()
    if clean_label in {"aheago", "ahegao"}:
        return "Disgust"
    return label.strip().title() if label else "Unknown"


def sync_ahegao_images():
    if not AHEGAO_DATASET_DIR.exists():
        return {"imported": 0, "total": 0, "folder": str(AHEGAO_DATASET_DIR), "exists": False}

    with get_db() as db:
        before = db.execute("SELECT COUNT(*) FROM emotion_images").fetchone()[0]
        rows = [
            (normalize_dataset_label("Ahegao"), "Ahegao", str(path), path.name)
            for path in AHEGAO_DATASET_DIR.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
        db.executemany(
            """
            INSERT OR IGNORE INTO emotion_images (label, source_label, file_path, filename)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        after = db.execute("SELECT COUNT(*) FROM emotion_images").fetchone()[0]

    return {"imported": after - before, "total": len(rows), "folder": str(AHEGAO_DATASET_DIR), "exists": True}


init_db()
sync_ahegao_images()


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    confirm_password = payload.get("confirmPassword") or ""

    if not username or not email or not password:
        return jsonify({"error": "Tous les champs sont obligatoires."}), 400
    if password != confirm_password:
        return jsonify({"error": "Les mots de passe ne sont pas identiques."}), 400

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Ce compte existe deja."}), 409

    return jsonify({"message": "Compte cree. Connectez-vous maintenant."}), 201


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email et mot de passe obligatoires."}), 400

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user is None:
        return jsonify({"error": "Compte inexistant."}), 404
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Mot de passe incorrect."}), 401

    return jsonify({"username": user["username"], "email": user["email"]})


@app.get("/api/model/status")
def model_status():
    return jsonify(predictor_status(get_predictor()))


@app.get("/api/dataset/status")
def dataset_status():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT label, COUNT(*) AS count
            FROM emotion_images
            GROUP BY label
            ORDER BY label
            """
        ).fetchall()
    return jsonify({"classes": [dict(row) for row in rows]})


@app.post("/api/dataset/sync")
def dataset_sync():
    return jsonify(sync_ahegao_images())


@app.get("/api/dataset/images")
def dataset_images():
    label = normalize_dataset_label(request.args.get("label") or "Disgust")
    try:
        limit = min(max(int(request.args.get("limit", 24)), 1), 120)
    except ValueError:
        limit = 24

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, label, source_label, filename
            FROM emotion_images
            WHERE label = ?
            ORDER BY id
            LIMIT ?
            """,
            (label, limit),
        ).fetchall()

    return jsonify(
        {
            "label": label,
            "images": [
                {
                    **dict(row),
                    "image_url": f"/api/dataset/images/{row['id']}/file",
                }
                for row in rows
            ],
        }
    )


@app.get("/api/dataset/images/<int:image_id>/file")
def dataset_image_file(image_id):
    with get_db() as db:
        row = db.execute("SELECT file_path FROM emotion_images WHERE id = ?", (image_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Image introuvable dans la base."}), 404

    path = Path(row["file_path"])
    if not path.exists() or path.suffix.lower() not in IMAGE_SUFFIXES:
        return jsonify({"error": "Fichier image introuvable."}), 404

    return send_file(path)


@app.post("/api/predict/dataset/<int:image_id>")
def predict_dataset_image(image_id):
    with get_db() as db:
        row = db.execute(
            "SELECT label, source_label, file_path, filename FROM emotion_images WHERE id = ?",
            (image_id,),
        ).fetchone()

    if row is None:
        return jsonify({"error": "Image introuvable dans la base."}), 404

    path = Path(row["file_path"])
    if not path.exists() or path.suffix.lower() not in IMAGE_SUFFIXES:
        return jsonify({"error": "Fichier image introuvable."}), 404

    prediction, boxed, face_found = predict_with_face_crop(str(path))
    return jsonify(
        {
            **prediction,
            "preview": boxed,
            "face_found": face_found,
            "database_label": row["label"],
            "source_label": row["source_label"],
            "filename": row["filename"],
        }
    )


@app.post("/api/model/load")
def load_model():
    global predictor
    model = request.files.get("model")
    if model is None:
        return jsonify({"error": "Aucun fichier .pth envoye."}), 400

    filename = secure_filename(model.filename or "model.pth") or "model.pth"
    target = ROOT_DIR / filename
    model.save(target)
    predictor = EmotionPredictor(target)
    status = predictor_status(predictor)
    return jsonify(status), 200 if predictor.ready else 400


@app.post("/api/predict/image")
def predict_image():
    image = request.files.get("image")
    if image is None:
        return jsonify({"error": "Aucune image envoyee."}), 400

    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        image.save(temp.name)
        prediction, boxed, face_found = predict_with_face_crop(temp.name)

    return jsonify({**prediction, "preview": boxed, "face_found": face_found})


@app.post("/api/predict/frame")
def predict_frame():
    payload = request.get_json(silent=True) or {}
    data_url = payload.get("image", "")
    if "," not in data_url:
        return jsonify({"error": "Frame invalide."}), 400

    raw = base64.b64decode(data_url.split(",", 1)[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
        temp.write(raw)
        temp.flush()
        prediction, boxed, face_found = predict_with_face_crop(temp.name)

    return jsonify({**prediction, "preview": boxed, "face_found": face_found})


def predict_with_face_crop(path):
    if cv2 is None:
        return {"error": "OpenCV non disponible: impossible de detecter le visage."}, "", False

    frame = cv2.imread(path)
    if frame is None:
        return {"error": "Image invalide ou frame vide."}, "", False

    prepared_frame = prepare_frame_for_detection(frame)
    output = prepared_frame.copy()
    face_box = detect_largest_face(output)
    face_found = face_box is not None

    if not face_found:
        preview = encode_frame(output)
        prediction = predict_full_frame(output)
        prediction["message"] = "Visage non detecte: prediction faite sur l'image complete."
        return prediction, preview, False

    x1, y1, x2, y2 = face_box
    face = prepared_frame[y1:y2, x1:x2]
    cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 255), 5)
    cv2.putText(output, "Face", (x1, max(30, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 3)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as face_temp:
        cv2.imwrite(face_temp.name, face)
        prediction = get_predictor().predict(face_temp.name)

    preview = encode_frame(output)
    return prediction, preview, True


def prepare_frame_for_detection(frame):
    height, width = frame.shape[:2]
    shortest_side = min(height, width)
    if shortest_side >= 520:
        return frame

    scale = min(4.0, 520 / max(1, shortest_side))
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_CUBIC)


def predict_full_frame(frame):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as frame_temp:
        cv2.imwrite(frame_temp.name, frame)
        return get_predictor().predict(frame_temp.name)


def detect_largest_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cascade_names = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_frontalface_alt.xml",
        "haarcascade_profileface.xml",
    ]
    all_faces = []
    min_size = max(24, min(frame.shape[:2]) // 12)

    for name in cascade_names:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        if cascade.empty():
            continue
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.04,
            minNeighbors=3,
            minSize=(min_size, min_size),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        all_faces.extend(faces)

    if not all_faces:
        return None

    x, y, w, h = max(all_faces, key=lambda box: box[2] * box[3])
    pad_x = int(w * 0.28)
    pad_y = int(h * 0.35)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(frame.shape[1], x + w + pad_x)
    y2 = min(frame.shape[0], y + h + pad_y)
    return x1, y1, x2, y2


def encode_frame(frame):
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
