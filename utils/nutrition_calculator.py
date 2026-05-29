"""
Nutrition & BMI calculator — BMI, TDEE, daily macro targets, meal tracking.
"""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

DB_PATH = Path(__file__).parent / "nutrition_db.json"
with open(DB_PATH) as f:
    NUTRITION_DB: dict = json.load(f)

ACTIVITY_MULTIPLIERS = {
    "sedentary":   1.2,
    "light":       1.375,
    "moderate":    1.55,
    "active":      1.725,
    "very_active": 1.9,
}

def calculate_bmi(weight_kg, height_cm):
    return round(weight_kg / (height_cm / 100) ** 2, 1)

def bmi_category(bmi):
    if bmi < 18.5: return "Underweight"
    if bmi < 25.0: return "Normal"
    if bmi < 30.0: return "Overweight"
    return "Obese"

def calculate_tdee(weight_kg, height_cm, age, gender, activity="moderate"):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr  = base + 5 if gender.lower() == "male" else base - 161
    return round(bmr * ACTIVITY_MULTIPLIERS.get(activity, 1.55))

def get_daily_requirements(weight_kg, height_cm, age, gender,
                            activity="moderate", goal="maintain"):
    tdee = calculate_tdee(weight_kg, height_cm, age, gender, activity)
    bmi  = calculate_bmi(weight_kg, height_cm)
    calories = tdee - 500 if goal == "lose" else tdee + 300 if goal == "gain" else tdee
    return {
        "calories": calories,
        "protein":  round((calories * 0.30) / 4),
        "carbs":    round((calories * 0.45) / 4),
        "fat":      round((calories * 0.25) / 9),
        "fiber":    25 if gender.lower() == "female" else 38,
        "bmi":      bmi,
        "bmi_category": bmi_category(bmi),
        "tdee":     tdee,
        "goal":     goal,
    }

def get_nutrition(food_name, quantity_g=None):
    entry = NUTRITION_DB.get(food_name)
    if not entry:
        return {"error": f"'{food_name}' not found"}
    serving = quantity_g if quantity_g else entry["serving_g"]
    scale   = serving / 100.0
    return {
        "food": food_name, "quantity": serving,
        "calories": round(entry["calories"] * scale, 1),
        "protein":  round(entry["protein"]  * scale, 1),
        "carbs":    round(entry["carbs"]    * scale, 1),
        "fat":      round(entry["fat"]      * scale, 1),
        "fiber":    round(entry["fiber"]    * scale, 1),
    }

def dietary_advice(intake: dict, targets: dict) -> list:
    advice = []
    remaining_cal = targets["calories"] - intake.get("calories", 0)
    remaining_pro = targets["protein"]  - intake.get("protein",  0)
    remaining_fib = targets["fiber"]    - intake.get("fiber",    0)
    fat_excess    = intake.get("fat", 0) - targets["fat"]

    if remaining_cal < -200:
        advice.append("You have exceeded today's calorie target.")
    elif remaining_cal > 500:
        advice.append(f"{int(remaining_cal)} kcal remaining — aim for balanced meals.")
    if remaining_pro > 20:
        advice.append(f"Add {int(remaining_pro)}g more protein — try dal, paneer, or eggs.")
    if remaining_fib > 10:
        advice.append("Boost fiber intake with vegetables, legumes, or whole grains.")
    if fat_excess > 15:
        advice.append("Fat intake is high today — prefer grilled over fried items tomorrow.")
    if not advice:
        advice.append("Great balance today! Keep it up.")
    return advice
