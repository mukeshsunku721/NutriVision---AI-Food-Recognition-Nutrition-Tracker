import os
import cv2
from ultralytics import YOLO
from .nutrition_calculator import get_nutrition

# Load model on CPU
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
model = None

if os.path.exists(MODEL_PATH):
    try:
        model = YOLO(MODEL_PATH)
        print("✅ YOLO Classification Model loaded.")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
else:
    print(f"⚠️  Model not found at {MODEL_PATH}")

def detect_and_annotate(image_path, quantity_g=100):
    img = cv2.imread(image_path)
    if img is None:
        raise Exception("Could not read image file.")

    detections = []
    
    if model is not None:
        # Run Classification Inference
        results = model(img, device='cpu')[0]
        
        # Check for Classification Results (probs)
        if hasattr(results, 'probs') and results.probs is not None:
            # Get the top predicted class
            top1_idx = results.probs.top1 
            conf = float(results.probs.top1conf)
            label = results.names[top1_idx]
            
            print(f"🎯 Predicted: {label} ({round(conf*100, 2)}%)")

            # Since there's no box, we'll draw a label at the top of the image
            cv2.putText(img, f"Detected: {label} ({round(conf*100,1)}%)", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (108, 99, 255), 2)
            
            # Draw a border around the whole image to show it was processed
            h, w, _ = img.shape
            cv2.rectangle(img, (0,0), (w-1, h-1), (108, 99, 255), 10)

            nutri = get_nutrition(label, quantity_g)
            
            detections.append({
                "index": 1,
                "label": label.replace("_", " ").title(),
                "food_name": label,
                "confidence": round(conf * 100, 1),
                "color_rgb": [108, 99, 255],
                "nutrition": nutri
            })
        else:
            print("❌ No classification probabilities found.")

    # Save output
    out_name = "annotated_" + os.path.basename(image_path)
    out_path = os.path.join("static", "results", out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, img)

    # Calculate totals
    plate_total = {
        "calories": round(sum(d["nutrition"]["calories"] for d in detections), 1) if detections else 0,
        "protein": round(sum(d["nutrition"]["protein"] for d in detections), 1) if detections else 0,
        "carbs": round(sum(d["nutrition"]["carbs"] for d in detections), 1) if detections else 0,
        "fat": round(sum(d["nutrition"]["fat"] for d in detections), 1) if detections else 0,
        "fiber": round(sum(d["nutrition"]["fiber"] for d in detections), 1) if detections else 0
    }

    return {
        "count": len(detections),
        "annotated_url": "/static/results/" + out_name, # Added for frontend compatibility
        "annotated_path": out_path,
        "detections": detections,
        "plate_total": plate_total
    }
