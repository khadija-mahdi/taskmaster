# api_server.py - Another Flask app on different port
from flask import Flask, jsonify
import os
import time

app = Flask(__name__)

@app.route('/')
def api_info():
    return jsonify({
        'service': 'API Server',
        'pid': os.getpid(),
        'port': 5001,
        'timestamp': time.time()
    })

@app.route('/data')
def get_data():
    return jsonify({'data': [1, 2, 3, 4, 5], 'source': 'api'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting API server on port {port} (PID: {os.getpid()})")
    app.run(host='0.0.0.0', port=port, debug=False)