from flask import Flask
import os
import threading

app = Flask(__name__)

@app.route('/')
def index():
    return "Sacerbot está rodando!", 200

@app.route('/health')
def health():
    return "Sacerbot Online", 200

def run_bot():
    import main
    main.bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
