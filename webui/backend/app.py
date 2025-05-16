from flask import Flask, jsonify
from flask_cors import CORS
import yaml
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

@app.route('/api/deadline')
def get_deadline():
    config = load_config()
    deadline = config.get('deadline')
    return jsonify({'deadline': deadline})

if __name__ == '__main__':
    app.run(debug=True)
