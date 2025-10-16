import chess
import chess.engine
from flask import Flask, request, jsonify
from flask_cors import CORS

# Asegúrate de que esta ruta sea correcta para tu sistema
STOCKFISH_PATH = "/home/dw/workspace/chess-app/stockfish/stockfish-ubuntu-x86-64-avx2"

app = Flask(__name__)
# Configuración más permisiva de CORS
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://0.0.0.0:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Inicializar el motor una sola vez al inicio
engine = None

def initialize_engine():
    """Inicializa el motor de ajedrez si aún no está inicializado."""
    global engine
    if engine is None:
        try:
            print("Inicializando Stockfish...")
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
            # Configurar Stockfish para mejor rendimiento
            engine.configure({"Skill Level": 20})  # Nivel máximo de habilidad
            print("Stockfish inicializado correctamente")
            return True
        except Exception as e:
            print(f"Error inicializando Stockfish: {e}")
            return False
    return True

# Inicializar el motor al importar el módulo
initialize_engine()

@app.route("/make_move", methods=["POST", "OPTIONS"])
def make_move():
    """
    Recibe una posición del tablero en formato FEN, calcula la mejor jugada con Stockfish
    y la devuelve.
    """
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    # Verificar que el motor esté inicializado
    global engine  # Declarar global al principio de la función
    if engine is None:
        if not initialize_engine():
            return jsonify({"error": "No se pudo inicializar Stockfish"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
            
        fen = data.get("fen")
        if not fen:
            return jsonify({"error": "FEN no proporcionado"}), 400

        print(f"Recibido FEN: {fen}")  # Debug
        
        board = chess.Board(fen)
        
        # Verificar si el juego ha terminado
        if board.is_game_over():
            return jsonify({"error": "El juego ha terminado"}), 400
        
        # Calcular la mejor jugada
        print("Calculando mejor jugada...")
        result = engine.play(board, chess.engine.Limit(time=2.0))
        best_move = result.move.uci()
        print(f"Mejor jugada calculada: {best_move}")  # Debug
        
        response = jsonify({
            "best_move": best_move,
            "fen_after_move": board.fen()  # FEN después del movimiento (opcional)
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
        
    except chess.engine.EngineTerminatedError:
        print("Motor terminado, reinicializando...")
        # Intentar reinicializar el motor
        try:
            if engine:
                engine.quit()
            engine = None
            if initialize_engine():
                # Reintentar la jugada
                board = chess.Board(fen)
                result = engine.play(board, chess.engine.Limit(time=2.0))
                best_move = result.move.uci()
                response = jsonify({"best_move": best_move})
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response
            else:
                return jsonify({"error": "Error reinicializando Stockfish"}), 500
        except Exception as e:
            return jsonify({"error": f"Error crítico: {str(e)}"}), 500
            
    except Exception as e:
        print(f"Error en make_move: {e}")  # Debug
        response = jsonify({"error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500

@app.route("/health", methods=["GET"])
def health():
    global engine
    response = jsonify({
        "status": "healthy", 
        "engine_initialized": engine is not None
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/")
def index():
    return "Servidor de ajedrez funcionando. ¡Listo para recibir jugadas!"

@app.route("/restart_engine", methods=["POST"])
def restart_engine():
    """Reinicia el motor Stockfish (útil si se cuelga)"""
    global engine
    try:
        if engine:
            engine.quit()
        engine = None
        success = initialize_engine()
        return jsonify({"success": success, "message": "Motor reiniciado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Manejar cierre graceful del servidor
import atexit

@atexit.register
def close_engine():
    global engine
    if engine:
        print("Cerrando Stockfish...")
        engine.quit()

if __name__ == "__main__":
    print("Iniciando servidor de ajedrez...")
    print(f"Usando Stockfish desde: {STOCKFISH_PATH}")
    # Verificar que el motor esté inicializado
    if engine is None and not initialize_engine():
        print("ERROR: No se pudo inicializar Stockfish. Verifica la ruta.")
    else:
        print("Servidor listo con Stockfish inicializado")
    # Ejecutar en todas las interfaces para evitar problemas de CORS
    app.run(host='0.0.0.0', port=5000, debug=True)