from flask import Flask, render_template, redirect, url_for, session, request
from flask_socketio import SocketIO
import socketio
import threading
import time
import secrets
import os

# Create required directories
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
socketio_server = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

USERS = {
    "admin": "leoni2025",
    "technicien": "test123"
}

client_socket = socketio.Client(reconnection=True, reconnection_attempts=10, reconnection_delay=1)
resultats_tests = {
    "Bobine": "⏳ En attente...",
    "Lames": "⏳ En attente...",
    "Capteurs": "⏳ En attente..."
}

connexion_etat = "🔴 Déconnecté"
connection_lock = threading.Lock()
is_connected = False
last_heartbeat = time.time()
HEARTBEAT_TIMEOUT = 10  # 10 seconds timeout

def check_heartbeat():
    """Monitor heartbeat and connection status"""
    global connexion_etat, is_connected, last_heartbeat
    while True:
        with connection_lock:
            if is_connected and (time.time() - last_heartbeat) > HEARTBEAT_TIMEOUT:
                is_connected = False
                connexion_etat = "🔴 Déconnecté"
                socketio_server.emit('update_connection_status', {'status': connexion_etat})
                try:
                    client_socket.disconnect()
                except:
                    pass
        time.sleep(2)

def connect_to_pi():
    """Maintain connection to Raspberry Pi"""
    global connexion_etat, is_connected, last_heartbeat
    retry_count = 0
    max_retries = 3

    while True:
        try:
            if not is_connected and not client_socket.connected:
                retry_count += 1
                client_socket.connect('http://192.168.137.2:5001', transports=['websocket'])
                with connection_lock:
                    is_connected = True
                    connexion_etat = "🟢 Connecté"
                    last_heartbeat = time.time()
                    socketio_server.emit('update_connection_status', {'status': connexion_etat})
                print("✅ Connexion réussie au Raspberry Pi")
                retry_count = 0  # Reset retry count on successful connection
            elif is_connected:
                # Send heartbeat when connected
                try:
                    client_socket.emit('heartbeat')
                    last_heartbeat = time.time()
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Erreur de connexion: {e}")
            if retry_count >= max_retries:
                time.sleep(10)  # Longer delay after max retries
                retry_count = 0
            else:
                time.sleep(2)  # Short delay between retries
        time.sleep(2)

@client_socket.on('connect')
def on_connect():
    global is_connected, connexion_etat, last_heartbeat
    with connection_lock:
        is_connected = True
        connexion_etat = "🟢 Connecté"
        last_heartbeat = time.time()
        socketio_server.emit('update_connection_status', {'status': connexion_etat})

@client_socket.on('disconnect')
def handle_disconnect():
    global connexion_etat, is_connected
    with connection_lock:
        if is_connected:
            is_connected = False
            connexion_etat = "🔴 Déconnecté"
            socketio_server.emit('update_connection_status', {'status': connexion_etat})

@client_socket.on('heartbeat_response')
def handle_heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()

# Start connection monitoring threads
threading.Thread(target=connect_to_pi, daemon=True).start()
threading.Thread(target=check_heartbeat, daemon=True).start()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', results=resultats_tests, connection_status=connexion_etat)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        error = 'Identifiants invalides'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@socketio_server.on('start_test')
def demarrer_test(data):
    if 'username' not in session:
        return

    type_test = data.get('type')
    print(f"🔹 Test demandé pour: {type_test}")

    if type_test in resultats_tests and is_connected:
        resultats_tests[type_test] = "Test en cours..."
        socketio_server.emit('update_result', {'type': type_test, 'result': "Test en cours..."})
        socketio_server.start_background_task(client_socket.emit, 'start_test', {'type': type_test})

@client_socket.on('update_result')
def recevoir_resultat(data):
    type_test = data.get('type')
    resultat = data.get('result')
    print(f"✅ Résultat reçu - Type: {type_test}, Résultat: {resultat}")

    if type_test in resultats_tests:
        resultats_tests[type_test] = resultat
        socketio_server.emit('update_result', {'type': type_test, 'result': resultat})

@socketio_server.on('connect')
def handle_connect():
    if 'username' not in session:
        return

    print("👤 Client connecté")
    for type_test, resultat in resultats_tests.items():
        socketio_server.emit('update_result', {'type': type_test, 'result': resultat})
    socketio_server.emit('update_connection_status', {'status': connexion_etat})

if __name__ == '__main__':
    print("\n=== 🎯 Serveur de diagnostic LEONI ===")
    print("📌 Accédez à l'interface en visitant :")
    print("→ http://localhost:5000")
    print("→ http://127.0.0.1:5000")
    print("=====================================\n")

    socketio_server.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)