import chess
import chess.engine
import os
import atexit
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Clase para encapsular la lógica de Stockfish ---
class StockfishEngine:
    """Una clase para gestionar la instancia del motor Stockfish."""
    def __init__(self, path):
        self.path = path
        self.engine = None
        self.initialize()

    def initialize(self):
        """Inicializa o reinicializa el motor de ajedrez."""
        if self.engine:
            try:
                self.engine.quit()
            except chess.engine.EngineTerminatedError:
                logging.warning("El motor ya estaba terminado antes de intentar cerrarlo.")
        
        try:
            logging.info(f"Inicializando Stockfish desde: {self.path}")
            self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
            self.engine.configure({"Skill Level": 20})  # Nivel máximo
            logging.info("Stockfish inicializado correctamente.")
            return True
        except Exception as e:
            logging.error(f"Error crítico inicializando Stockfish: {e}")
            self.engine = None
            return False

    def get_best_move(self, board, time_limit=2.0):
        """Calcula la mejor jugada para una posición dada."""
        if not self.is_ready():
            logging.error("Intento de obtener jugada pero el motor no está listo.")
            raise chess.engine.EngineTerminatedError("El motor no está inicializado.")
        
        try:
            result = self.engine.play(board, chess.engine.Limit(time=time_limit))
            return result.move
        except chess.engine.EngineTerminatedError as e:
            logging.error(f"El motor se ha terminado inesperadamente: {e}")
            # Intentar reinicializar para la próxima solicitud
            self.initialize()
            raise  # Relanzar la excepción para que el endpoint la maneje

    def is_ready(self):
        """Verifica si el motor ha sido inicializado."""
        # En versiones antiguas de python-chess, no hay una forma fiable de 
        # verificar si el proceso está vivo sin causar un error. 
        # Simplemente comprobamos si el objeto fue creado.
        return self.engine is not None

    def close(self):
        """Cierra el motor de ajedrez de forma segura."""
        if self.engine:
            logging.info("Cerrando Stockfish...")
            self.engine.quit()

# --- Configuración de la aplicación Flask ---
app = Flask(__name__)
CORS(app) # Configuración de CORS simplificada y permisiva para desarrollo

# La ruta a Stockfish se puede configurar con la variable de entorno STOCKFISH_PATH
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stockfish", "stockfish-ubuntu-x86-64-avx2"))

# Crear una instancia única del motor
stockfish_engine = StockfishEngine(STOCKFISH_PATH)

# Registrar el cierre del motor al salir de la aplicación
atexit.register(stockfish_engine.close)


# --- Endpoints de la API ---
@app.route("/")
def index():
    return "Servidor de ajedrez funcionando. ¡Listo para recibir jugadas!"

@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar el estado del servidor y del motor."""
    engine_ready = stockfish_engine.is_ready()
    status = {
        "status": "healthy" if engine_ready else "unhealthy",
        "engine_initialized": engine_ready
    }
    return jsonify(status), 200 if engine_ready else 503

@app.route("/restart_engine", methods=["POST"])
def restart_engine():
    """Endpoint para forzar el reinicio del motor Stockfish."""
    logging.info("Solicitud de reinicio del motor recibida.")
    success = stockfish_engine.initialize()
    if success:
        return jsonify({"success": True, "message": "Motor reiniciado correctamente."})
    else:
        return jsonify({"success": False, "message": "Error al reiniciar el motor."}), 500

@app.route("/make_move", methods=["POST"])
def make_move():
    """
    Recibe una posición FEN, calcula la mejor jugada y la devuelve.
    """
    data = request.get_json()
    if not data or "fen" not in data:
        return jsonify({"error": "FEN no proporcionado."}), 400

    fen = data["fen"]
    try:
        board = chess.Board(fen)
    except ValueError:
        return jsonify({"error": "FEN inválido."}), 400

    if board.is_game_over():
        return jsonify({"status": "El juego ha terminado.", "best_move": None}), 200

    try:
        logging.info(f"Calculando jugada para FEN: {fen}")
        best_move = stockfish_engine.get_best_move(board)
        logging.info(f"Mejor jugada calculada: {best_move.uci()}")
        return jsonify({"best_move": best_move.uci()})

    except chess.engine.EngineTerminatedError:
        return jsonify({"error": "El motor de ajedrez no está disponible, se está reiniciando."}), 503
    except Exception as e:
        logging.error(f"Error inesperado en make_move: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

# --- Ejecución del servidor ---
if __name__ == "__main__":
    # El modo debug no es recomendable para producción
    # Para producción, usa un servidor WSGI como Gunicorn: gunicorn --bind 0.0.0.0:5000 server:app
    if not stockfish_engine.is_ready():
        logging.error("El servidor arranca, pero el motor Stockfish no se pudo inicializar.")
    else:
        logging.info("Servidor listo con Stockfish inicializado.")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
