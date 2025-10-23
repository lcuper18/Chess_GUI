import chess
import chess.engine
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import uuid
from flask import send_file, send_from_directory

app = Flask(__name__)
CORS(app)  # Permitir requests desde web/Android

# Configuración del motor (usando tu misma configuración)
CFISH_PATH = os.environ.get("STOCKFISH_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines/Cfish_Linux", "Cfish 060821 x64 general"))

# Estado global del juego
partidas = {}
motor_lock = threading.Lock()

def inicializar_motor():
    """Inicializa el motor de chess usando tu configuración"""
    try:
        # Cambiar al directorio del motor para que encuentre el archivo NNUE
        motor_dir = os.path.dirname(CFISH_PATH)
        motor_nombre = os.path.basename(CFISH_PATH)
        os.chdir(motor_dir)
        
        engine = chess.engine.SimpleEngine.popen_uci(f"./{motor_nombre}")
        print("✅ Motor de chess inicializado correctamente")
        return engine
    except Exception as e:
        print(f"❌ Error iniciando motor: {e}")
        return None

# Motor global (se reutiliza)
engine = inicializar_motor()

def tablero_a_json(board):
    """Convierte un tablero de chess a formato JSON para el frontend"""
    tablero_json = []
    
    # Crear matriz 8x8 para el frontend (de arriba a abajo, de a-h)
    for fila in range(7, -1, -1):  # De 7 a 0 (de arriba a abajo)
        for col in range(8):
            square = chess.square(col, fila)
            pieza = board.piece_at(square)
            
            pieza_info = None
            if pieza:
                # Determinar tipo y color
                tipo = pieza.symbol().lower()
                color = 'white' if pieza.color == chess.WHITE else 'black'
                
                pieza_info = {
                    'tipo': tipo,
                    'color': color,
                    'simbolo': pieza.symbol(),
                    'unicode': obtener_unicode_pieza(pieza.symbol())
                }
            
            tablero_json.append({
                'casilla': chess.square_name(square),
                'fila': 8 - fila,  # 1-8
                'columna': chr(97 + col),  # a-h
                'pieza': pieza_info,
                'color_casilla': 'light' if (fila + col) % 2 == 0 else 'dark'
            })
    
    return {
        'posiciones': tablero_json,
        'fen': board.fen(),
        'es_turno_blancas': board.turn == chess.WHITE,
        'jugadas_legales': [move.uci() for move in board.legal_moves],
        'es_jaque': board.is_check(),
        'es_jaque_mate': board.is_checkmate(),
        'es_tablas': board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition(),
        'resultado': board.result() if board.is_game_over() else None
    }

def obtener_unicode_pieza(simbolo):
    """Devuelve el símbolo Unicode para la pieza"""
    unicode_piezas = {
        'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
        'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟'
    }
    return unicode_piezas.get(simbolo, simbolo)

@app.route('/api/nueva-partida', methods=['POST'])
def nueva_partida():
    """Crea una nueva partida contra Cfish"""
    try:
        partida_id = str(uuid.uuid4())
        board = chess.Board()
        
        partidas[partida_id] = {
            'board': board,
            'historial': [],
            'creado': time.time(),
            'jugador_color': 'white'  # Humano juega con blancas
        }
        
        print(f"🎮 Nueva partida creada: {partida_id}")
        
        return jsonify({
            'success': True,
            'partida_id': partida_id,
            'tablero': tablero_a_json(board),
            'mensaje': 'Partida creada. Eres las blancas!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/estado/<partida_id>', methods=['GET'])
def obtener_estado(partida_id):
    """Obtiene el estado actual de una partida"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        partida = partidas[partida_id]
        board = partida['board']
        
        estado = {
            'success': True,
            'tablero': tablero_a_json(board),
            'historial': partida['historial'],
            'es_turno_humano': board.turn == chess.WHITE,
            'juego_terminado': board.is_game_over(),
            'movimientos_totales': len(partida['historial'])
        }
        
        if board.is_game_over():
            estado['resultado'] = board.result()
            estado['terminacion'] = str(board.outcome().termination) if board.outcome() else 'unknown'
        
        return jsonify(estado)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jugar/<partida_id>', methods=['POST'])
def jugar_movimiento(partida_id):
    """Ejecuta un movimiento del jugador humano"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        data = request.get_json()
        if not data or 'movimiento' not in data:
            return jsonify({'success': False, 'error': 'Movimiento no proporcionado'}), 400
        
        movimiento_uci = data.get('movimiento', '').strip().lower()
        
        partida = partidas[partida_id]
        board = partida['board']
        
        # Verificar que es turno del humano
        if board.turn != chess.WHITE:
            return jsonify({'success': False, 'error': 'No es tu turno'}), 400
        
        # Validar movimiento (igual que en tu código)
        try:
            move = chess.Move.from_uci(movimiento_uci)
            if move not in board.legal_moves:
                return jsonify({
                    'success': False, 
                    'error': 'Movimiento ilegal',
                    'jugadas_legales': [m.uci() for m in board.legal_moves]
                }), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de movimiento inválido. Use notación UCI (ej: e2e4)'}), 400
        
        # Ejecutar movimiento humano (igual que en tu código)
        board.push(move)
        notacion_san = board.san(move)
        
        partida['historial'].append({
            'jugador': 'humano',
            'movimiento': movimiento_uci,
            'notacion': notacion_san,
            'timestamp': time.time()
        })
        
        print(f"👤 Jugador jugó: {movimiento_uci} ({notacion_san}) en partida {partida_id}")
        
        respuesta = {
            'success': True,
            'movimiento_ejecutado': movimiento_uci,
            'notacion': notacion_san,
            'tablero': tablero_a_json(board),
            'juego_terminado': board.is_game_over()
        }
        
        # Si el juego continúa, hacer que juegue el motor (igual que en tu código)
        if not board.is_game_over():
            threading.Thread(target=jugar_motor, args=(partida_id,)).start()
            respuesta['motor_pensando'] = True
            respuesta['mensaje'] = 'Cfish está pensando...'
        else:
            respuesta['resultado'] = board.result()
            print(f"🏁 Partida {partida_id} terminada: {board.result()}")
        
        return jsonify(respuesta)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def jugar_motor(partida_id):
    """Función para que juegue el motor (basada en tu código)"""
    if partida_id not in partidas:
        return
    
    partida = partidas[partida_id]
    board = partida['board']
    
    # Pequeña pausa para mejor UX
    time.sleep(0.5)
    
    if board.is_game_over() or board.turn == chess.WHITE:
        return
    
    with motor_lock:
        try:
            print(f"🤖 Motor pensando en partida {partida_id}...")
            
            # Usar la misma configuración de tiempo que en tu código
            result = engine.play(board, chess.engine.Limit(time=2.0))
            move = result.move
            
            # Actualizar el board
            board.push(move)
            notacion_san = board.san(move)
            
            partida['historial'].append({
                'jugador': 'motor',
                'movimiento': move.uci(),
                'notacion': notacion_san,
                'timestamp': time.time()
            })
                
            print(f"🤖 Motor jugó: {move.uci()} ({notacion_san}) en partida {partida_id}")
            
        except Exception as e:
            print(f"❌ Error del motor en partida {partida_id}: {e}")

@app.route('/api/jugadas-legales/<partida_id>', methods=['GET'])
def obtener_jugadas_legales(partida_id):
    """Obtiene todas las jugadas legales para una posición"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        board = partidas[partida_id]['board']
        jugadas = [move.uci() for move in board.legal_moves]
        
        return jsonify({
            'success': True,
            'jugadas_legales': jugadas,
            'es_turno_humano': board.turn == chess.WHITE,
            'total_jugadas': len(jugadas)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rendirse/<partida_id>', methods=['POST'])
def rendirse(partida_id):
    """El jugador se rinde"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        partida = partidas[partida_id]
        partida['historial'].append({
            'jugador': 'sistema',
            'evento': 'El jugador se rindió',
            'timestamp': time.time()
        })
        
        return jsonify({
            'success': True,
            'mensaje': 'Te has rendido',
            'resultado': '0-1'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/partidas', methods=['GET'])
def listar_partidas():
    """Lista todas las partidas activas"""
    try:
        partidas_lista = []
        for pid, partida in partidas.items():
            partidas_lista.append({
                'partida_id': pid,
                'creado': partida['creado'],
                'movimientos': len(partida['historial']),
                'terminada': partida['board'].is_game_over(),
                'resultado': partida['board'].result() if partida['board'].is_game_over() else 'en_progreso'
            })
        
        return jsonify({
            'success': True,
            'partidas': partidas_lista,
            'total': len(partidas_lista)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reiniciar/<partida_id>', methods=['POST'])
def reiniciar_partida(partida_id):
    """Reinicia una partida existente"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        partidas[partida_id] = {
            'board': chess.Board(),
            'historial': [],
            'creado': time.time(),
            'jugador_color': 'white'
        }
        
        return jsonify({
            'success': True,
            'mensaje': 'Partida reiniciada',
            'tablero': tablero_a_json(partidas[partida_id]['board'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/info', methods=['GET'])
def info_api():
    """Información sobre la API"""
    return jsonify({
        'name': 'Chess Cfish API',
        'version': '1.0',
        'engine': 'Cfish',
        'endpoints': {
            'nueva_partida': 'POST /api/nueva-partida',
            'estado': 'GET /api/estado/<partida_id>',
            'jugar': 'POST /api/jugar/<partida_id>',
            'jugadas_legales': 'GET /api/jugadas-legales/<partida_id>',
            'rendirse': 'POST /api/rendirse/<partida_id>',
            'partidas': 'GET /api/partidas',
            'reiniciar': 'POST /api/reiniciar/<partida_id>'
        }
    })

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica que el servidor y motor estén funcionando"""
    motor_activo = engine is not None
    return jsonify({
        'status': 'healthy' if motor_activo else 'degraded',
        'motor_activo': motor_activo,
        'partidas_activas': len(partidas),
        'timestamp': time.time()
    })

@app.route('/')
def index():
    """Redirige al manual HTML"""
    try:
        return send_file('docs/manual.html')
    except:
        # Si no existe, mostrar página simple
        return '''
        <html>
        <head><title>Chess API</title></head>
        <body>
            <h1>Chess Cfish API</h1>
            <p>El manual está en <a href="/docs/manual.html">/docs/manual.html</a></p>
            <p><a href="/api/health">Health Check</a></p>
        </body>
        </html>
        '''

@app.route('/docs/<path:filename>')
def serve_docs(filename):
    """Sirve archivos de documentación"""
    return send_from_directory('docs', filename)

if __name__ == '__main__':
    if engine:
        print("🚀 Servidor de Chess API iniciado!")
        print("📡 Disponible en: http://localhost:5000")
        print("🔧 Motor configurado desde: {}".format(CFISH_PATH))
        print("\n📋 Endpoints principales:")
        print("   POST /api/nueva-partida     - Crear nueva partida")
        print("   POST /api/jugar/<id>        - Jugar movimiento")
        print("   GET  /api/estado/<id>       - Estado de partida")
        print("   GET  /api/jugadas-legales/<id> - Jugadas legales")
        print("   GET  /api/health            - Estado del servidor")
        
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    else:
        print("❌ No se pudo iniciar el motor de chess. Verifica la configuración.")