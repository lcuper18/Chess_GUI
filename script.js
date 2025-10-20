// Este script utiliza jQuery, que es una dependencia de chessboard.js
$(document).ready(function() {
    // --- Variables Globales y Configuración ---
    let board = null; // El objeto del tablero visual
    const game = new Chess(); // El motor de lógica del ajedrez
    const SERVER_URL = 'http://localhost:5000';

    // Elementos del DOM cacheados para eficiencia
    const statusElement = $('#status');
    const fenElement = $('#fen');
    const moveHistoryElement = $('#moveHistory');
    const spinner = $('#thinkingSpinner');
    const serverStatusElement = $('#serverStatus');

    // --- Manejadores de Eventos del Tablero ---

    // Se llama cuando el usuario empieza a arrastrar una pieza
    function onDragStart(source, piece) {
        // No permitir mover piezas si la partida ha terminado
        if (game.game_over()) return false;

        // Solo permitir mover las piezas del jugador cuyo turno es
        if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
            (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
            return false;
        }
    }

    // Se llama cuando el usuario suelta una pieza en una casilla
    function onDrop(source, target) {
        // Intentar hacer el movimiento en la lógica del juego
        const move = game.move({
            from: source,
            to: target,
            promotion: 'q' // Nota: siempre promocionar a reina por simplicidad
        });

        // Si el movimiento es ilegal, `game.move` devuelve null. `snapback` devuelve la pieza a su origen.
        if (move === null) return 'snapback';

        // Si el movimiento es legal, actualizar el estado y la UI
        updateStatus();
    }

    // Se llama después de que la animación de la pieza termina
    function onSnapEnd() {
        // Asegura que la posición del tablero visual coincida con la del motor lógico
        board.position(game.fen());
    }

    // --- Funciones de Actualización de la UI ---

    function updateStatus() {
        let statusText = '';
        const turn = game.turn() === 'b' ? 'Negras' : 'Blancas';

        if (game.in_checkmate()) {
            statusText = `Jaque Mate, ganan las ${turn === 'Blancas' ? 'Negras' : 'Blancas'}`;
        } else if (game.in_draw()) {
            statusText = 'Empate por tablas, ahogado o repetición';
        } else {
            statusText = `Turno de las ${turn}`;
            if (game.in_check()) {
                statusText += ', las Negras están en Jaque';
            }
        }

        statusElement.text(statusText);
        fenElement.text(game.fen());
        updateMoveHistory();
    }

    function updateMoveHistory() {
        moveHistoryElement.html('');
        const history = game.history({ verbose: true });
        for (let i = 0; i < history.length; i += 2) {
            const moveNumber = Math.floor(i / 2) + 1;
            const whiteMove = history[i] ? history[i].san : '';
            const blackMove = history[i + 1] ? history[i + 1].san : '';
            moveHistoryElement.append(`<div class="move-number">${moveNumber}.</div><div class="move">${whiteMove}</div><div class="move">${blackMove || ''}</div>`);
        }
        // Auto-scroll hacia el último movimiento
        moveHistoryElement.scrollTop(moveHistoryElement.prop("scrollHeight"));
    }

    // --- Lógica del Servidor y Botones ---

    async function getBestMove() {
        const controls = $('.controls button');
        controls.prop('disabled', true);
        spinner.css('display', 'flex');
        statusElement.text('Consultando a Stockfish...');

        try {
            const response = await fetch(`${SERVER_URL}/make_move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fen: game.fen() })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Error HTTP: ${response.status}` }));
                throw new Error(errorData.error);
            }

            const data = await response.json();
            if (data.error) throw new Error(data.error);

            if (data.best_move) {
                game.move(data.best_move, { sloppy: true });
                board.position(game.fen());
                updateStatus();
            }
        } catch (error) {
            statusElement.text(`Error: ${error.message}`);
            console.error('Error obteniendo la mejor jugada:', error);
        } finally {
            controls.prop('disabled', false);
            spinner.css('display', 'none');
            checkServerConnection(); // Re-verificar estado del servidor
        }
    }

    function checkServerConnection() {
        fetch(`${SERVER_URL}/health`)
            .then(response => {
                if (!response.ok) throw new Error('Respuesta no OK');
                return response.json();
            })
            .then(data => {
                serverStatusElement.text(`✅ Servidor conectado - Motor: ${data.engine_initialized ? 'Activo' : 'Inactivo'}`);
                serverStatusElement.removeClass('disconnected').addClass('connected');
            })
            .catch(error => {
                serverStatusElement.text('❌ Error de conexión con el servidor.');
                serverStatusElement.removeClass('connected').addClass('disconnected');
            });
    }

    // --- Inicialización ---

    const boardConfig = {
        draggable: true,
        position: 'start',
        pieceTheme: 'img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };
    board = Chessboard('board', boardConfig); // Inicializar el tablero visual

    // Asignar eventos a los botones
    $('#getMoveBtn').on('click', getBestMove);
    $('#resetBtn').on('click', () => {
        game.reset();
        board.start();
        updateStatus();
    });
    $('#flipBoardBtn').on('click', board.flip);
    $('#undoBtn').on('click', () => {
        game.undo(); // Deshace en la lógica
        if (game.turn() !== 'b') { // Si es turno de blancas, deshacer también la jugada de la máquina
            game.undo();
        }
        board.position(game.fen()); // Actualiza el tablero visual
        updateStatus();
    });

    // Ajustar el tamaño del tablero si la ventana cambia de tamaño
    $(window).resize(board.resize);

    // Estado inicial
    updateStatus();
    checkServerConnection();
    setInterval(checkServerConnection, 30000); // Verificar conexión cada 30 segundos
});
