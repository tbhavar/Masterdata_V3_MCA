import os
import base64
import ddddocr
import io
import string
import numpy as np
import cv2
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize OCR engine
ocr = ddddocr.DdddOcr(show_ad=False)

def is_valid_captcha(s):
    # MCA captchas are typically alphanumeric
    if not s or len(s) < 4: return False
    allowed = string.ascii_letters + string.digits
    return any(c in allowed for c in s)

def surgical_clean(img_bytes):
    # 1. Decode bytes to OpenCV image
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    # 2. Upscale (3x for ultra-precision)
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    
    # 3. Binary Threshold (Everything becomes 255/White or 0/Black)
    # Binary inverse so characters are White (255) and background is Black (0) for analysis
    _, binary = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY_INV)
    
    # 4. Connected Components with Stats
    # This finds every "island" of pixels
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    
    # Create empty mask to hold only the characters
    cleaned = np.zeros_like(binary)
    
    # 5. Surgical Filter: Loop over islands and keep only those of a certain size
    for i in range(1, num_labels): # Start from 1 (0 is background)
        area = stats[i, cv2.CC_STAT_AREA]
        # Standard MCA grid intersection is < 150px (after 3x upscale)
        # Standard character is usually > 300px
        if area > 100: 
            cleaned[labels == i] = 255
            
    # 6. Final cleanup: Morphological Dilation to reconnect any character segments
    kernel = np.ones((2,2), np.uint8)
    cleaned = cv2.dilate(cleaned, kernel, iterations=1)
    
    # 7. Convert back to original White background, Black text (what ddddocr likes)
    final_img = cv2.bitwise_not(cleaned)
    
    # Save debug image
    cv2.imwrite("debug_captcha.png", final_img)
    
    # Convert back to PNG bytes
    _, buffer = cv2.imencode('.png', final_img)
    return buffer.tobytes()

@app.route('/solve', methods=['POST'])
def solve_captcha():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        img_data = data['image'].split(",")[-1]
        img_bytes = base64.b64decode(img_data)
        
        # --- Surgical Mode (OpenCV) ---
        processed_bytes = surgical_clean(img_bytes)
        
        # Solve using ddddocr
        result = ocr.classification(processed_bytes)
        
        # Evaluation
        display_result = result
        if not is_valid_captcha(result):
            display_result = "ERROR"
            
        print(f"Solved (Surgical Mode): {display_result} (Raw: {result})")
        return jsonify({"result": display_result})
        
    except Exception as e:
        print(f"OCR Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("="*50)
    print("MCA OCR Server is running on http://localhost:5000")
    print("Keep this window open while using the extension.")
    print("="*50)
    app.run(host='0.0.0.0', port=5000)
