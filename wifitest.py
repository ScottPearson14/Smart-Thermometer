from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "ESP32 Temperature Server is running!"

@app.route('/test')
def test_endpoint():
    return jsonify({"message": "Server is running!", "timestamp": datetime.now().isoformat()})

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        # Get JSON data from ESP32
        data = request.json
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Print received data
        print(f"[{timestamp}] Received data from ESP32:")
        print(f"  Temperature 1: {data.get('test_temp1', 'N/A')}°C")
        print(f"  Temperature 2: {data.get('test_temp2', 'N/A')}°C")
        print(f"  ESP32 Timestamp: {data.get('timestamp', 'N/A')}ms")
        print("-" * 50)
        
        # Send confirmation back to ESP32
        return jsonify({"status": "success", "message": "Data received"}), 200
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    print("Starting ESP32 Temperature Server...")
    print("Test the server: http://127.0.0.1:8080/test")
    print("ESP32 will send data to: http://YOUR_IP:8080/data")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
