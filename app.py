from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Sacerbot está rodando!", 200

@app.route('/health')
def health():
    return "Sacerbot Online", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
