import chess
import chess.engine
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import uuid
from flask import send_file, send_from_directory
import atexit
import signal

app = Flask(__name__)
CORS(app)  # Permitir requests desde web/Android

# Configuración del motor (usando tu misma configuración)
CFISH_PATH = os.environ.get("STOCKFISH_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines/Cfish_Linux", "Cfish 060821 x64 general"))

# Configuración de límites
MAX_PARTIDAS = 100
MAX_TIEMPO_PARTIDA = 24 * 60 * 60  # 24 horas

# Estado global del juego
partidas = {}
motor_lock = threading.Lock()

def inicializar_motor():
    """Inicializa el motor de chess con manejo robusto de errores"""
    try:
        motor_dir = os.path.dirname(CFISH_PATH)
        motor_nombre = os.path.basename(CFISH_PATH)
        
        # Guardar directorio actual para restaurarlo después
        directorio_original = os.getcwd()
        
        if not os.path.exists(CFISH_PATH):
            print(f"❌ Archivo del motor no encontrado: {CFISH_PATH}")
            return None
            
        os.chdir(motor_dir)
        engine = chess.engine.SimpleEngine.popen_uci(f"./{motor_nombre}")
        
        # Restaurar directorio original
        os.chdir(directorio_original)
        
        # Configurar parámetros del motor
        engine.configure({"Hash": 256, "Threads": 2})
        
        print("✅ Motor de chess inicializado correctamente")
        return engine
        
    except Exception as e:
        print(f"❌ Error crítico iniciando motor: {e}")
        # Restaurar directorio en caso de error
        if 'directorio_original' in locals():
            os.chdir(directorio_original)
        return None

# Cierre graceful del motor
def cerrar_motor():
    """Cierra el motor de ajedrez de forma segura"""
    global engine
    if engine:
        try:
            engine.quit()
            print("✅ Motor de chess cerrado correctamente")
        except Exception as e:
            print(f"⚠️ Error cerrando motor: {e}")
        finally:
            engine = None

# Registrar handlers para cierre graceful
atexit.register(cerrar_motor)
def signal_handler(sig, frame):
    print(f"\n🛑 Recibida señal {sig}, cerrando...")
    cerrar_motor()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Motor global (se reutiliza)
engine = inicializar_motor()

def limpiar_partidas_antiguas():
    """Limpia partidas antiguas automáticamente"""
    ahora = time.time()
    partidas_a_eliminar = []
    
    for partida_id, partida in partidas.items():
        tiempo_vida = ahora - partida['creado']
        if (tiempo_vida > MAX_TIEMPO_PARTIDA or 
            len(partidas) > MAX_PARTIDAS and partida['board'].is_game_over()):
            partidas_a_eliminar.append(partida_id)
    
    for partida_id in partidas_a_eliminar:
        del partidas[partida_id]
        print(f"🧹 Partida {partida_id} eliminada por limpieza automática")

# Ejecutar limpieza periódica
def iniciar_limpieza_periodica():
    def limpiar_periodicamente():
        while True:
            time.sleep(3600)  # Cada hora
            with motor_lock:
                limpiar_partidas_antiguas()
    
    threading.Thread(target=limpiar_periodicamente, daemon=True).start()

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
        # Limpieza automática antes de crear nueva partida
        if len(partidas) >= MAX_PARTIDAS:
            limpiar_partidas_antiguas()
        
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
        print(f"❌ Error en nueva_partida: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/estado/<partida_id>', methods=['GET'])
def obtener_estado(partida_id):
    """Obtiene el estado actual de una partida con información extendida"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        partida = partidas[partida_id]
        board = partida['board']
        
        estado = {
            'success': True,
            'partida_id': partida_id,
            'tablero': tablero_a_json(board),
            'historial': partida['historial'][-10:],  # Últimos 10 movimientos
            'es_turno_humano': board.turn == chess.WHITE,
            'juego_terminado': board.is_game_over(),
            'movimientos_totales': len(partida['historial']),
            'motor_activo': engine is not None
        }
        
        if board.is_game_over():
            outcome = board.outcome()
            estado['resultado'] = board.result()
            estado['terminacion'] = str(outcome.termination) if outcome else 'unknown'
            estado['ganador'] = 'blancas' if outcome and outcome.winner == chess.WHITE else \
                              'negras' if outcome and outcome.winner == chess.BLACK else 'tablas'
        
        return jsonify(estado)
        
    except Exception as e:
        print(f"❌ Error en obtener_estado: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/jugar/<partida_id>', methods=['POST'])
def jugar_movimiento(partida_id):
    """Ejecuta un movimiento del jugador humano con validaciones mejoradas"""
    try:
        # Validar partida
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        # Validar datos de entrada
        data = request.get_json()
        if not data or 'movimiento' not in data:
            return jsonify({'success': False, 'error': 'Movimiento no proporcionado'}), 400
        
        movimiento_uci = data.get('movimiento', '').strip().lower()
        
        # Validar formato básico
        if len(movimiento_uci) < 4 or len(movimiento_uci) > 5:
            return jsonify({'success': False, 'error': 'Formato de movimiento inválido'}), 400
        
        partida = partidas[partida_id]
        board = partida['board']
        
        # Verificar que el juego no ha terminado
        if board.is_game_over():
            return jsonify({
                'success': False, 
                'error': 'La partida ha terminado',
                'resultado': board.result()
            }), 400
        
        # Verificar que es turno del humano
        if board.turn != chess.WHITE:
            return jsonify({
                'success': False, 
                'error': 'No es tu turno',
                'es_turno_humano': False
            }), 400
        
        # Validar movimiento
        try:
            move = chess.Move.from_uci(movimiento_uci)
            if move not in board.legal_moves:
                return jsonify({
                    'success': False, 
                    'error': 'Movimiento ilegal',
                    'jugadas_legales': [m.uci() for m in board.legal_moves]
                }), 400
        except ValueError as ve:
            return jsonify({
                'success': False, 
                'error': f'Formato de movimiento inválido: {str(ve)}'
            }), 400
        
        # Ejecutar movimiento humano
        board.push(move)
        notacion_san = board.san(move)
        
        partida['historial'].append({
            'jugador': 'humano',
            'movimiento': movimiento_uci,
            'notacion': notacion_san,
            'timestamp': time.time()
        })
        
        print(f"👤 Jugador jugó: {movimiento_uci} ({notacion_san}) en partida {partida_id}")
        
        # Preparar respuesta
        respuesta = {
            'success': True,
            'movimiento_ejecutado': movimiento_uci,
            'notacion': notacion_san,
            'tablero': tablero_a_json(board),
            'juego_terminado': board.is_game_over(),
            'es_turno_humano': False  # Ahora es turno del motor
        }
        
        # Manejar fin del juego
        if board.is_game_over():
            resultado = board.result()
            respuesta['resultado'] = resultado
            respuesta['mensaje'] = f'Partida terminada: {resultado}'
            print(f"🏁 Partida {partida_id} terminada: {resultado}")
        else:
            # Iniciar movimiento del motor en segundo plano
            if engine is not None:
                threading.Thread(target=jugar_motor, args=(partida_id,), daemon=True).start()
                respuesta['motor_pensando'] = True
                respuesta['mensaje'] = 'Cfish está pensando...'
            else:
                respuesta['error'] = 'Motor no disponible'
                respuesta['motor_pensando'] = False
        
        return jsonify(respuesta)
        
    except Exception as e:
        print(f"❌ Error en jugar_movimiento: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

def jugar_motor(partida_id):
    """Función mejorada para que juegue el motor con mejor manejo de errores"""
    if partida_id not in partidas:
        return
    
    partida = partidas[partida_id]
    board = partida['board']
    
    # Verificaciones adicionales
    if (board.is_game_over() or 
        board.turn == chess.WHITE or 
        engine is None):
        return
    
    # Pausa para mejor UX
    time.sleep(0.5)
    
    with motor_lock:
        try:
            print(f"🤖 Motor pensando en partida {partida_id}...")
            
            # Configuración robusta con timeout
            limit = chess.engine.Limit(time=2.0)
            result = engine.play(board, limit)
            
            if result.move is None:
                print(f"⚠️ Motor no devolvió movimiento en partida {partida_id}")
                return
                
            move = result.move
            
            # Verificar que el movimiento es legal
            if move not in board.legal_moves:
                print(f"❌ Movimiento ilegal del motor: {move.uci()}")
                return
            
            # Ejecutar movimiento
            board.push(move)
            notacion_san = board.san(move)
            
            partida['historial'].append({
                'jugador': 'motor',
                'movimiento': move.uci(),
                'notacion': notacion_san,
                'timestamp': time.time()
            })
                
            print(f"🤖 Motor jugó: {move.uci()} ({notacion_san}) en partida {partida_id}")
            
        except chess.engine.EngineTerminatedError:
            print(f"❌ Motor terminado inesperadamente en partida {partida_id}")
        except Exception as e:
            print(f"❌ Error del motor en partida {partida_id}: {e}")

@app.route('/api/jugadas-legales/<partida_id>', methods=['GET'])
def obtener_jugadas_legales(partida_id):
    """Obtiene todas las jugadas legales para una posición"""
    try:
        if partida_id not in partidas:
            return jsonify({'success': False, 'error': 'Partida no encontrada'}), 404
        
        board = partidas[partida_id]['board']
        
        # Verificar que no es juego terminado
        if board.is_game_over():
            return jsonify({
                'success': True,
                'jugadas_legales': [],
                'es_turno_humano': board.turn == chess.WHITE,
                'total_jugadas': 0,
                'juego_terminado': True
            })
        
        jugadas = [move.uci() for move in board.legal_moves]
        
        return jsonify({
            'success': True,
            'jugadas_legales': jugadas,
            'es_turno_humano': board.turn == chess.WHITE,
            'total_jugadas': len(jugadas),
            'juego_terminado': False
        })
        
    except Exception as e:
        print(f"❌ Error en obtener_jugadas_legales: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

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
        print(f"❌ Error en rendirse: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/partidas', methods=['GET'])
def listar_partidas():
    """Lista todas las partidas activas"""
    try:
        partidas_lista = []
        for pid, partida in partidas.items():
            board = partida['board']
            partidas_lista.append({
                'partida_id': pid,
                'creado': partida['creado'],
                'movimientos': len(partida['historial']),
                'terminada': board.is_game_over(),
                'resultado': board.result() if board.is_game_over() else 'en_progreso',
                'ultimo_movimiento': partida['historial'][-1] if partida['historial'] else None
            })
        
        return jsonify({
            'success': True,
            'partidas': sorted(partidas_lista, key=lambda x: x['creado'], reverse=True),
            'total': len(partidas_lista),
            'limite': MAX_PARTIDAS
        })
        
    except Exception as e:
        print(f"❌ Error en listar_partidas: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

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
        print(f"❌ Error en reiniciar_partida: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/api/info', methods=['GET'])
def info_api():
    """Información sobre la API"""
    return jsonify({
        'name': 'Chess Cfish API',
        'version': '1.1',
        'engine': 'Cfish',
        'motor_activo': engine is not None,
        'partidas_activas': len(partidas),
        'limite_partidas': MAX_PARTIDAS,
        'endpoints': {
            'nueva_partida': 'POST /api/nueva-partida',
            'estado': 'GET /api/estado/<partida_id>',
            'jugar': 'POST /api/jugar/<partida_id>',
            'jugadas_legales': 'GET /api/jugadas-legales/<partida_id>',
            'rendirse': 'POST /api/rendirse/<partida_id>',
            'partidas': 'GET /api/partidas',
            'reiniciar': 'POST /api/reiniciar/<partida_id>',
            'health': 'GET /api/health',
            'info': 'GET /api/info'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica que el servidor y motor estén funcionando con más detalles"""
    motor_activo = engine is not None
    estado_motor = "healthy" if motor_activo else "degraded"
    
    # Verificar que el motor responde
    motor_responsive = False
    if motor_activo:
        try:
            with motor_lock:
                # Test rápido del motor
                board = chess.Board()
                engine.ping()
            motor_responsive = True
        except:
            motor_responsive = False
            estado_motor = "degraded"
    
    return jsonify({
        'status': estado_motor,
        'motor_activo': motor_activo,
        'motor_responsive': motor_responsive,
        'partidas_activas': len(partidas),
        'partidas_terminadas': sum(1 for p in partidas.values() if p['board'].is_game_over()),
        'timestamp': time.time(),
        'version': '1.1'
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
        <head>
            <title>Chess API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                a { color: #007bff; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .endpoint { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; }
            </style>
        </head>
        <body>
            <h1>♟️ Chess Cfish API</h1>
            <p>API de ajedrez con motor Cfish</p>
            
            <h2>📚 Documentación</h2>
            <p>El manual está en <a href="/docs/manual.html">/docs/manual.html</a></p>
            
            <h2>🔍 Endpoints principales</h2>
            <div class="endpoint"><strong>GET</strong> <a href="/api/health">/api/health</a> - Estado del servidor</div>
            <div class="endpoint"><strong>GET</strong> <a href="/api/info">/api/info</a> - Información de la API</div>
            <div class="endpoint"><strong>POST</strong> /api/nueva-partida - Crear nueva partida</div>
            <div class="endpoint"><strong>GET</strong> <a href="/api/partidas">/api/partidas</a> - Listar partidas</div>
            
            <p><strong>Versión:</strong> 1.1</p>
            <p><strong>Motor:</strong> {}</p>
        </body>
        </html>
        '''.format("Cfish ✅" if engine else "Cfish ❌ (No disponible)")

@app.route('/docs/<path:filename>')
def serve_docs(filename):
    """Sirve archivos de documentación"""
    return send_from_directory('docs', filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'success': False, 'error': 'Método no permitido'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

if __name__ == '__main__':
    if engine:
        # Iniciar limpieza automática
        iniciar_limpieza_periodica()
        
        print("🚀 Servidor de Chess API iniciado!")
        print("📡 Disponible en: http://localhost:5000")
        print("🔧 Motor configurado desde: {}".format(CFISH_PATH))
        print("🛡️  Modo: {}".format("DEBUG" if os.environ.get('FLASK_DEBUG') else "PRODUCTION"))
        print("📊 Límite de partidas: {}".format(MAX_PARTIDAS))
        print("\n📋 Endpoints principales:")
        print("   POST /api/nueva-partida     - Crear nueva partida")
        print("   POST /api/jugar/<id>        - Jugar movimiento")
        print("   GET  /api/estado/<id>       - Estado de partida")
        print("   GET  /api/jugadas-legales/<id> - Jugadas legales")
        print("   GET  /api/health            - Estado del servidor")
        
        # Configuración de producción
        debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        
        app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=debug_mode, 
            threaded=True,
            use_reloader=debug_mode  # Evitar reloader en producción
        )
    else:
        print("❌ No se pudo iniciar el motor de chess. Verifica la configuración.")
        print("💡 Asegúrate de que:")
        print("   - La ruta CFISH_PATH es correcta: {}".format(CFISH_PATH))
        print("   - El archivo del motor existe y tiene permisos de ejecución")
        print("   - Las dependencias del motor (libs) están instaladas")
        exit(1)