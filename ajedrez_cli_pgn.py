from stockfish import Stockfish
from colorama import Fore, Style, init
import os
import time
from datetime import datetime

# Inicializar colorama
init(autoreset=True)

# Ruta al ejecutable de Stockfish (ajústala según tu sistema)
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stockfish", "stockfish-ubuntu-x86-64-avx2"))

# Configurar el motor
stockfish = Stockfish(
    path=STOCKFISH_PATH,
    parameters={
        "Threads": 2,
        "Minimum Thinking Time": 200
    }
)

stockfish.set_skill_level(8)  # de 0 (fácil) a 20 (máximo nivel)

# Historial global de jugadas
historial = []

def limpiar_pantalla():
    os.system("clear" if os.name == "posix" else "cls")

def mostrar_tablero():
    """Muestra el tablero visualmente con color"""
    board = stockfish.get_board_visual()
    print(Fore.CYAN + "\n" + board + "\n" + Style.RESET_ALL)

def mostrar_historial():
    """Muestra las jugadas realizadas"""
    if not historial:
        print(Fore.YELLOW + "Aún no hay jugadas registradas.\n")
        return

    print(Fore.YELLOW + "Historial de jugadas:")
    for i in range(0, len(historial), 2):
        blancas = historial[i]
        negras = historial[i + 1] if i + 1 < len(historial) else ""
        print(f"{(i // 2) + 1}. {blancas:<7} {negras}")
    print()

def mostrar_estado():
    """Indica si hay ventaja, jaque o mate"""
    info = stockfish.get_evaluation()
    score = info.get('value')
    tipo = info.get('type')

    if tipo == 'mate':
        print(Fore.MAGENTA + f"⚠️ ¡Jaque mate en {abs(score)} movimientos!" + Style.RESET_ALL)
    elif tipo == 'cp':
        if score > 100:
            print(Fore.GREEN + f"Ventaja blanca (+{round(score/100,2)})")
        elif score < -100:
            print(Fore.RED + f"Ventaja negra ({round(score/100,2)})")
        else:
            print(Fore.YELLOW + "Posición equilibrada")
    print()

def guardar_pgn(resultado="*"):
    """Guarda la partida en formato PGN"""
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"partida_{fecha}_ajedrez_vs_stockfish.pgn"

    pgn = []
    pgn.append(f"[Event \"Partida contra Stockfish CLI\"]")
    pgn.append(f"[Site \"Linux Terminal\"]")
    pgn.append(f"[Date \"{datetime.now().strftime('%Y.%m.%d')}\"]")
    pgn.append(f"[White \"Humano\"]")
    pgn.append(f"[Black \"Stockfish\"]")
    pgn.append(f"[Result \"{resultado}\"]\n")

    jugadas_pgn = ""
    for i in range(0, len(historial), 2):
        blancas = historial[i]
        negras = historial[i + 1] if i + 1 < len(historial) else ""
        jugadas_pgn += f"{(i // 2) + 1}. {blancas} {negras} "

    pgn.append(jugadas_pgn.strip())
    pgn.append(f"\n\n{resultado}\n")

    with open(nombre_archivo, "w") as f:
        f.write("\n".join(pgn))

    print(Fore.CYAN + f"\n💾 Partida guardada como: {nombre_archivo}\n")

def iniciar_juego():
    limpiar_pantalla()
    print(Fore.CYAN + "♟️  Bienvenido a tu partida contra Stockfish (CLI + PGN Edition)\n")
    print(Fore.WHITE + "Usa tu tablero físico y escribe tus jugadas en formato UCI (ejemplo: e2e4, g1f3).")
    print("Escribe 'salir' para terminar la partida.\n")
    print("-" * 60)

    stockfish.set_position([])
    global historial
    historial = []

    resultado = "*"

    while True:
        mostrar_tablero()
        mostrar_historial()
        mostrar_estado()

        jugada = input(Fore.GREEN + "Tu jugada ➤ " + Style.RESET_ALL).strip().lower()
        if jugada == "salir":
            resultado = "1/2-1/2"  # se considera empate si se abandona
            print("\nPartida finalizada por el jugador. Resultado: tablas (1/2-1/2)")
            break

        if not stockfish.is_move_correct(jugada):
            print(Fore.RED + "⚠️ Jugada inválida, intenta de nuevo.\n")
            time.sleep(1.5)
            limpiar_pantalla()
            continue

        # Jugada del humano
        stockfish.make_moves_from_current_position([jugada])
        historial.append(jugada)

        # Verificar si la IA tiene jugadas
        if stockfish.get_best_move() is None:
            mostrar_tablero()
            print(Fore.GREEN + "✅ ¡Has ganado! El motor no tiene jugadas legales.")
            resultado = "1-0"
            break

        # Turno de Stockfish
        print(Fore.CYAN + "\n🤖 Stockfish está pensando...\n" + Style.RESET_ALL)
        movimiento_ia = stockfish.get_best_move()
        time.sleep(0.8)

        stockfish.make_moves_from_current_position([movimiento_ia])
        historial.append(movimiento_ia)
        print(Fore.CYAN + f"🤖 Stockfish juega: {movimiento_ia}\n")

        # Pausa antes de refrescar
        time.sleep(1.2)
        limpiar_pantalla()

    guardar_pgn(resultado)
    print(Fore.MAGENTA + "Gracias por jugar. ¡Analiza tu partida en Lichess o Arena!\n")

if __name__ == "__main__":
    iniciar_juego()
