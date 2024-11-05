from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import io
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    
    # Read the image into memory and encode it for the request
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    _, encoded_image = cv2.imencode('.jpg', img)
    image_bytes = encoded_image.tobytes()
    
    # Set up request to external server
    server_url = "http://4.240.46.255:1337/upload"
    files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
    data = {
        "query": "I am providing business cards. I want JSON output with keys like name, company name, mobile number, email, and address in a structured format."
    }
    
    try:
        # Send the image and query to the server
        start_time = time.perf_counter()
        response = requests.post(server_url, files=files, data=data, timeout=30)
        end_time = time.perf_counter() - start_time

        # Print the server response and time taken in the console
        if response.status_code == 200:
            response_json = response.json()
            print("Response received:", response_json)
            print("Response time:", end_time, "seconds")
            return jsonify(response_json)
        else:
            print("Error response:", response.status_code, response.text)
            return jsonify({'error': 'Failed to process image on external server'}), 500

    except requests.RequestException as e:
        print("Request failed:", e)
        return jsonify({'error': 'Request to external server failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=9999)
