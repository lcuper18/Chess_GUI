import chess
import chess.engine
import os

# Configuración correcta
CFISH_PATH = "/home/dw/workspace/Chess_GUI/engines/Cfish_Linux/Cfish 060821 x64 general"

def jugar_vs_cfish():
    # Cambiar al directorio del motor para que encuentre el archivo NNUE
    motor_dir = os.path.dirname(CFISH_PATH)
    motor_nombre = os.path.basename(CFISH_PATH)
    os.chdir(motor_dir)
    
    board = chess.Board()
    
    try:
        print("🚀 Iniciando motor Cfish...")
        # Usar ruta relativa desde el directorio actual
        engine = chess.engine.SimpleEngine.popen_uci(f"./{motor_nombre}")
        print("✅ Motor iniciado correctamente!")
        
    except Exception as e:
        print(f"❌ Error al iniciar el motor: {e}")
        return

    try:
        while not board.is_game_over():
            print("\n" + str(board))
            print(f"♟️  Turno: {'Blancas (Tú)' if board.turn == chess.WHITE else 'Negras (Cfish)'}")
            
            if board.turn == chess.WHITE:
                # Jugador humano
                while True:
                    try:
                        move_uci = input("🎮 Tu jugada (UCI, ej: e2e4): ").strip()
                        if not move_uci:
                            continue
                            
                        if move_uci.lower() in ['quit', 'exit', 'salir']:
                            print("👋 ¡Hasta luego!")
                            return
                            
                        move = chess.Move.from_uci(move_uci)
                        if move in board.legal_moves:
                            break
                        else:
                            print("❌ Jugada ilegal. Intenta otra vez.")
                    except ValueError:
                        print("❌ Formato inválido. Usa formato UCI (ej: e2e4, g1f3)")
                    
            else:
                # Motor Cfish
                print("🤖 Cfish pensando...")
                try:
                    # Usar un tiempo razonable para la búsqueda
                    result = engine.play(
                        board, 
                        chess.engine.Limit(time=2.0)
                    )
                    move = result.move
                    print(f"✅ Cfish juega: {move.uci()}")
                    
                except Exception as e:
                    print(f"💥 Error durante la búsqueda: {e}")
                    break

            board.push(move)

        print("\n" + "="*50)
        print("🏁 Partida terminada!")
        print(f"📊 Resultado: {board.result()}")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n⏹️ Partida interrumpida por el usuario")
    finally:
        try:
            engine.quit()
            print("🔌 Motor cerrado correctamente")
        except:
            pass

if __name__ == "__main__":
    jugar_vs_cfish()