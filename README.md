# NutriVision: AI-Powered Indian Food Recognition & Nutrition Tracker

NutriVision is a full-stack AI application designed to identify various Indian food items from images and provide instant nutritional profiling (Calories, Protein, Carbs, and Fats). 

The project bridges the gap between complex Indian cuisine and automated dietary tracking by leveraging State-of-the-Art (SOTA) Computer Vision and regional nutritional databases.

## 🚀 Features
- **AI Recognition:** Powered by **YOLOv8** to detect North and South Indian dishes (Idli, Dosa, Biryani, Chikki, etc.).
- **Nutritional Insights:** Real-time lookup of macro-nutrients based on the **Indian Food Composition Tables (IFCT)**.
- **Personalized Dashboard:** Track daily caloric intake against BMI-calculated requirements.
- **Fuzzy Matching Logic:** High-reliability mapping between AI labels and database entries.

## 🛠️ Tech Stack
- **Deep Learning:** YOLOv8 (Ultralytics), PyTorch
- **Backend:** Python, Flask
- **Data:** Pandas, SQLite, IFCT Database
- **Frontend:** HTML5, CSS3, JavaScript (AJAX, Chart.js)
- **Environment:** Google Colab (Training), Local Flask Server (Deployment)

## 📁 Project Structure
```text

Nutrivision Project/
│
├── app.py		# Main Flask server
├── requirements.txt
├── Food_Detection_YOLOv8.ipynb
│
├── instance/		# User's log database 
│   └── nutrition.db
│
├── models/		# Contains 'best.pt' (Trained YOLOv8 Weights)
│   └── best.pt
│
├── templates/		# Dashboard and Onboarding UI
│   ├── index.html
│   ├── dashboard.html
│   └── weekly.html
│
├── static/		# CSS, JS, and user-uploaded images
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   ├── dashboard.js
│   │   └── onboarding.js
│   │
│   ├── uploads/
│   └── results/
│
└── utils/
    ├── detector.py	# YOLOv8 Inference Logic
    ├── nutrition_calculator.py # Math & CSV Lookup Logic
    ├── nutrition_db.json
    └── __init__.py
```

## 📊 Dataset Information
To solve the lack of diverse Indian food data, I engineered a custom dataset by merging and balancing four major Kaggle sources:
Indian Food Images (Sourav Banerjee)
Indian Food Image Dataset (Bhavik Jikadara)
5000 Indian Cuisines (CampusX)
Indian Food Nutrition (Batthula Vinay)


## 🔧 Installation & Usage

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/NutriVision-Food-Detection.git
   cd NutriVision-Food-Detection/flask_app

