"""
Flask Web App — Food Detection + Nutrition Tracking
Endpoints:
  GET  /                        → onboarding page
  GET  /dashboard               → main dashboard
  POST /api/users               → create user
  GET  /api/users/<id>          → get user + daily requirements
  POST /api/detect              → upload plate image → circles + nutrition
  POST /api/users/<id>/meals    → log detected items as a meal
  GET  /api/users/<id>/summary  → daily intake vs targets
  GET  /api/users/<id>/weekly   → 7-day history
"""

import os, uuid, json
from datetime import date, datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from utils.detector import detect_and_annotate
from utils.nutrition_calculator import (
    get_daily_requirements, get_nutrition, dietary_advice
)

app = Flask(__name__)
CORS(app)
app.config.update(
    SECRET_KEY             = os.getenv("SECRET_KEY", "dev-secret"),
    SQLALCHEMY_DATABASE_URI= os.getenv("DATABASE_URI", "sqlite:///nutrition.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS = False,
    UPLOAD_FOLDER          = os.getenv("UPLOAD_FOLDER", "static/uploads"),
    RESULTS_FOLDER         = "static/results",
    MAX_CONTENT_LENGTH     = 16 * 1024 * 1024,
)
ALLOWED = {"jpg", "jpeg", "png", "webp"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULTS_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)


# ── Models ────────────────────────────────────────────────────────────────────
class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    age        = db.Column(db.Integer,  nullable=False)
    gender     = db.Column(db.String(10), nullable=False)
    height_cm  = db.Column(db.Float,    nullable=False)
    weight_kg  = db.Column(db.Float,    nullable=False)
    activity   = db.Column(db.String(20), default="moderate")
    goal       = db.Column(db.String(20), default="maintain")
    created_at = db.Column(db.DateTime,  default=datetime.utcnow)
    logs       = db.relationship("MealLog", backref="user", lazy=True)

    def to_dict(self):
        reqs = get_daily_requirements(
            self.weight_kg, self.height_cm, self.age,
            self.gender, self.activity, self.goal
        )
        return {
            "id": self.id, "name": self.name,
            "age": self.age, "gender": self.gender,
            "height_cm": self.height_cm, "weight_kg": self.weight_kg,
            "activity": self.activity, "goal": self.goal,
            "daily_requirements": reqs,
        }


class MealLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    meal_name  = db.Column(db.String(50),  nullable=False)
    food_name  = db.Column(db.String(100), nullable=False)
    quantity_g = db.Column(db.Float,  default=100.0)
    calories   = db.Column(db.Float,  default=0.0)
    protein    = db.Column(db.Float,  default=0.0)
    carbs      = db.Column(db.Float,  default=0.0)
    fat        = db.Column(db.Float,  default=0.0)
    fiber      = db.Column(db.Float,  default=0.0)
    image_path = db.Column(db.String(300))
    confidence = db.Column(db.Float)
    log_date   = db.Column(db.Date,     default=date.today)
    logged_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "meal_name": self.meal_name,
            "food_name": self.food_name,
            "label": self.food_name.replace("_"," ").title(),
            "quantity_g": self.quantity_g,
            "calories": self.calories, "protein": self.protein,
            "carbs": self.carbs, "fat": self.fat, "fiber": self.fiber,
            "image_path": self.image_path, "confidence": self.confidence,
            "log_date": str(self.log_date),
            "logged_at": self.logged_at.isoformat(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

def aggregate(logs):
    totals = {k: 0.0 for k in ("calories","protein","carbs","fat","fiber")}
    for log in logs:
        for k in totals: totals[k] += getattr(log, k)
    return {k: round(v, 1) for k, v in totals.items()}


# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/weekly")
def weekly_page():
    return render_template("weekly.html")


# ── User API ──────────────────────────────────────────────────────────────────
@app.route("/api/users", methods=["POST"])
def create_user():
    d = request.get_json()
    for f in ("name","age","gender","height_cm","weight_kg"):
        if f not in d:
            return jsonify({"error": f"Missing: {f}"}), 400
    user = User(name=d["name"], age=int(d["age"]), gender=d["gender"],
                height_cm=float(d["height_cm"]), weight_kg=float(d["weight_kg"]),
                activity=d.get("activity","moderate"), goal=d.get("goal","maintain"))
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@app.route("/api/users/<int:uid>", methods=["GET"])
def get_user(uid):
    return jsonify(db.get_or_404(User, uid).to_dict())

@app.route("/api/users/<int:uid>", methods=["PUT"])
def update_user(uid):
    user = db.get_or_404(User, uid)
    d = request.get_json()
    for f in ("name","age","gender","height_cm","weight_kg","activity","goal"):
        if f in d: setattr(user, f, d[f])
    db.session.commit()
    return jsonify(user.to_dict())


# ── DETECT — core endpoint ────────────────────────────────────────────────────
@app.route("/api/detect", methods=["POST"])
def detect():
    """
    Accepts a plate image.
    Returns:
      - annotated image path (circles drawn around each food item)
      - per-item detections with nutrition
      - plate-level totals
    """
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file or not allowed(file.filename):
        return jsonify({"error": "Invalid file type — use jpg/png"}), 400

    quantity_g = float(request.form.get("quantity_g", 100.0))

    filename  = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        result = detect_and_annotate(save_path, quantity_g=quantity_g)
    except Exception as e:
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

    # Make paths web-accessible
    result["original_url"]  = f"/static/uploads/{filename}"
    result["annotated_url"] = "/" + result["annotated_path"].replace("\\", "/")

    return jsonify(result)


# ── Meal logging ──────────────────────────────────────────────────────────────
@app.route("/api/users/<int:uid>/meals", methods=["POST"])
def log_meals(uid):
    """
    Log one or more detected food items as a meal.
    Body: { meal_name, items: [{food_name, quantity_g, confidence, image_path}], log_date? }
    """
    db.get_or_404(User, uid)
    d     = request.get_json()
    items = d.get("items", [])
    if not items:
        return jsonify({"error": "No items to log"}), 400

    logged = []
    for item in items:
        n = get_nutrition(item["food_name"], item.get("quantity_g", 100))
        if "error" in n:
            continue
        log = MealLog(
            user_id    = uid,
            meal_name  = d.get("meal_name", "Meal"),
            food_name  = item["food_name"],
            quantity_g = item.get("quantity_g", 100),
            calories   = n["calories"], protein = n["protein"],
            carbs      = n["carbs"],    fat     = n["fat"],
            fiber      = n["fiber"],
            image_path = item.get("image_path"),
            confidence = item.get("confidence"),
            log_date   = date.fromisoformat(d["log_date"]) if "log_date" in d else date.today(),
        )
        db.session.add(log)
        logged.append(log)
    db.session.commit()
    return jsonify({"logged": len(logged), "items": [l.to_dict() for l in logged]}), 201

@app.route("/api/users/<int:uid>/meals", methods=["GET"])
def get_meals(uid):
    db.get_or_404(User, uid)
    target = date.fromisoformat(request.args.get("date", str(date.today())))
    logs   = MealLog.query.filter_by(user_id=uid, log_date=target)\
                          .order_by(MealLog.logged_at).all()
    meals  = {}
    for log in logs:
        meals.setdefault(log.meal_name, []).append(log.to_dict())
    return jsonify({"date": str(target), "meals": meals})


# ── Summary ───────────────────────────────────────────────────────────────────
@app.route("/api/users/<int:uid>/summary", methods=["GET"])
def summary(uid):
    user   = db.get_or_404(User, uid)
    target = date.fromisoformat(request.args.get("date", str(date.today())))
    logs   = MealLog.query.filter_by(user_id=uid, log_date=target).all()
    intake  = aggregate(logs)
    targets = get_daily_requirements(
        user.weight_kg, user.height_cm, user.age,
        user.gender, user.activity, user.goal
    )
    remaining = {k: round(targets[k] - intake.get(k, 0), 1)
                 for k in ("calories","protein","carbs","fat","fiber")}
    advice = dietary_advice(intake, targets)
    return jsonify({
        "date": str(target), "intake": intake,
        "targets": targets, "remaining": remaining,
        "advice": advice, "log_count": len(logs),
    })

@app.route("/api/users/<int:uid>/weekly", methods=["GET"])
def weekly(uid):
    from datetime import timedelta
    user = db.get_or_404(User, uid)
    end  = date.today()
    start= end - timedelta(days=6)
    logs = MealLog.query.filter(
        MealLog.user_id==uid, MealLog.log_date>=start, MealLog.log_date<=end
    ).all()
    daily = {}
    for log in logs:
        d = str(log.log_date)
        daily.setdefault(d, {k:0.0 for k in ("calories","protein","carbs","fat","fiber")})
        for k in daily[d]: daily[d][k] += getattr(log, k)
    for d in daily: daily[d] = {k: round(v,1) for k,v in daily[d].items()}
    return jsonify({"start": str(start), "end": str(end), "daily": daily})


# ── Boot ──────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
