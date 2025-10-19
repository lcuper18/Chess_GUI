// Representación del estado del juego
let gameState = {
    board: Array(8).fill().map(() => Array(8).fill(null)),
    currentPlayer: 'white',
    selectedPiece: null,
    possibleMoves: [],
    moveHistory: [],
    boardFlipped: false
};

// URL base del servidor (¡Asegúrate de que tu servidor Stockfish esté corriendo aquí!)
const SERVER_URL = 'http://localhost:5000'; 

// --- Funciones de Inicialización y Conexión ---

// Inicializar el tablero
function initializeBoard() {
    const chessboard = document.getElementById('chessboard');
    chessboard.innerHTML = '';

    // Configuración inicial de piezas
    const initialSetup = [
        ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
        ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
        [null, null, null, null, null, null, null, null],
        [null, null, null, null, null, null, null, null],
        [null, null, null, null, null, null, null, null],
        [null, null, null, null, null, null, null, null],
        ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
        ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr']
    ];

    // Crear el tablero
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const square = document.createElement('div');
            square.className = `square ${(row + col) % 2 === 0 ? 'light' : 'dark'}`;
            square.dataset.row = row;
            square.dataset.col = col;

            // Asignar pieza si existe
            const piece = initialSetup[row][col];
            if (piece) {
                square.textContent = getPieceSymbol(piece);
                gameState.board[row][col] = piece;
            }

            square.addEventListener('click', () => handleSquareClick(row, col));
            chessboard.appendChild(square);
        }
    }

    updateStatus();
    checkServerConnection();
    
    // Forzar FEN inicial correcto
    document.getElementById('fen').textContent = getInitialFEN();
}

// Verificar conexión con el servidor
async function checkServerConnection() {
    const statusElement = document.getElementById('serverStatus');
    try {
        const response = await fetch(`${SERVER_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            statusElement.textContent = `✅ Servidor conectado - Motor: ${data.engine_initialized ? 'Activo' : 'Inactivo'}`;
            statusElement.className = 'server-status connected';
        } else {
            throw new Error('Servidor no responde correctamente');
        }
    } catch (error) {
        statusElement.textContent = `❌ Error de conexión: ${error.message}`;
        statusElement.className = 'server-status disconnected';
        console.error('Error de conexión:', error);
        addDebugInfo(`Error de conexión: ${error.message}`);
    }
}

// --- Funciones de Utilidad ---

// Agregar información de debug
function addDebugInfo(message) {
    const debugElement = document.getElementById('debugInfo');
    const timestamp = new Date().toLocaleTimeString();
    debugElement.innerHTML += `[${timestamp}] ${message}<br>`;
    debugElement.scrollTop = debugElement.scrollHeight;
}

// Obtener símbolo Unicode para la pieza
function getPieceSymbol(piece) {
    const symbols = {
        'wp': '♙', 'wr': '♖', 'wn': '♘', 'wb': '♗', 'wq': '♕', 'wk': '♔',
        'bp': '♟', 'br': '♜', 'bn': '♞', 'bb': '♝', 'bq': '♛', 'bk': '♚'
    };
    return symbols[piece] || '';
}

// Obtener elemento de casilla
function getSquareElement(row, col) {
    return document.querySelector(`.square[data-row="${row}"][data-col="${col}"]`);
}

// Verificar si una posición es válida
function isValidPosition(row, col) {
    return row >= 0 && row < 8 && col >= 0 && col < 8;
}

// Verificar si un movimiento es posible
function isPossibleMove(row, col) {
    return gameState.possibleMoves.some(move => move.row === row && move.col === col);
}

function getInitialFEN() {
    return 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
}

// --- Lógica del Tablero y Movimiento ---

// Manejar clic en una casilla
function handleSquareClick(row, col) {
    const piece = gameState.board[row][col];
    
    // Si hay una pieza seleccionada y se hace clic en una casilla de movimiento posible
    if (gameState.selectedPiece && isPossibleMove(row, col)) {
        movePiece(gameState.selectedPiece.row, gameState.selectedPiece.col, row, col);
        clearSelection();
        return;
    }

    // Si no hay pieza seleccionada, seleccionar esta pieza si es del jugador actual
    if (piece && piece[0] === gameState.currentPlayer[0]) {
        selectPiece(row, col, piece);
    } else {
        clearSelection();
    }
}

// Seleccionar una pieza
function selectPiece(row, col, piece) {
    clearSelection();
    gameState.selectedPiece = { row, col, type: piece };
    
    // Resaltar la casilla seleccionada
    const square = getSquareElement(row, col);
    square.classList.add('selected');
    
    // Calcular movimientos posibles (simplificado para demo)
    gameState.possibleMoves = calculatePossibleMoves(row, col, piece);
    
    // Resaltar movimientos posibles
    gameState.possibleMoves.forEach(move => {
        const moveSquare = getSquareElement(move.row, move.col);
        moveSquare.classList.add('possible-move');
    });
}

// Calcular movimientos posibles (versión simplificada)
function calculatePossibleMoves(row, col, piece) {
    const moves = [];
    const color = piece[0];
    const type = piece[1];
    
    // Movimientos básicos para peones (muy simplificado)
    if (type === 'p') {
        const direction = color === 'w' ? -1 : 1;
        
        // Movimiento hacia adelante
        if (isValidPosition(row + direction, col) && !gameState.board[row + direction][col]) {
            moves.push({ row: row + direction, col });
            
            // Doble movimiento inicial
            if ((color === 'w' && row === 6) || (color === 'b' && row === 1)) {
                if (!gameState.board[row + 2 * direction][col]) {
                    moves.push({ row: row + 2 * direction, col });
                }
            }
        }
        
        // Capturas diagonales
        if (isValidPosition(row + direction, col - 1) && 
            gameState.board[row + direction][col - 1] && 
            gameState.board[row + direction][col - 1][0] !== color) {
            moves.push({ row: row + direction, col: col - 1 });
        }
        
        if (isValidPosition(row + direction, col + 1) && 
            gameState.board[row + direction][col + 1] && 
            gameState.board[row + direction][col + 1][0] !== color) {
            moves.push({ row: row + direction, col: col + 1 });
        }
    }
    
    return moves;
}

// Mover una pieza
function movePiece(fromRow, fromCol, toRow, toCol) {
    const piece = gameState.board[fromRow][fromCol];
    
    // Verificar si es una captura
    const targetPiece = gameState.board[toRow][toCol];
    if (targetPiece) {
        addDebugInfo(`Captura: ${piece} captura ${targetPiece} en ${String.fromCharCode(97 + toCol)}${8 - toRow}`);
    }
    
    // Mover la pieza
    gameState.board[toRow][toCol] = piece;
    gameState.board[fromRow][fromCol] = null;
    
    // Actualizar la representación visual
    const fromSquare = getSquareElement(fromRow, fromCol);
    const toSquare = getSquareElement(toRow, toCol);
    
    toSquare.textContent = fromSquare.textContent;
    fromSquare.textContent = '';
    
    // Registrar el movimiento
    const fromFile = String.fromCharCode(97 + fromCol);
    const fromRank = 8 - fromRow;
    const toFile = String.fromCharCode(97 + toCol);
    const toRank = 8 - toRow;
    const moveNotation = `${fromFile}${fromRank}${toFile}${toRank}`;
    
    gameState.moveHistory.push(moveNotation);
    updateMoveHistory();
    
    // Cambiar turno
    gameState.currentPlayer = gameState.currentPlayer === 'white' ? 'black' : 'white';
    updateStatus();
    
    addDebugInfo(`Movimiento: ${moveNotation}`);
}

// Aplicar movimiento desde notación algebraica (ej: "e2e4")
function applyMoveFromNotation(move) {
    // Convertir notación UCI a coordenadas 
    const fromCol = move.charCodeAt(0) - 97;
    const fromRow = 8 - parseInt(move[1]);
    const toCol = move.charCodeAt(2) - 97;
    const toRow = 8 - parseInt(move[3]);
    
    movePiece(fromRow, fromCol, toRow, toCol);
}

// Limpiar selección
function clearSelection() {
    if (gameState.selectedPiece) {
        const square = getSquareElement(gameState.selectedPiece.row, gameState.selectedPiece.col);
        square.classList.remove('selected');
        
        gameState.possibleMoves.forEach(move => {
            const moveSquare = getSquareElement(move.row, move.col);
            moveSquare.classList.remove('possible-move');
        });
        
        gameState.selectedPiece = null;
        gameState.possibleMoves = [];
    }
}

// --- Funciones de Estado e Interfaz ---

// Actualizar el estado del juego (turno)
function updateStatus() {
    const statusElement = document.getElementById('status');
    statusElement.textContent = `Turno de las ${gameState.currentPlayer === 'white' ? 'Blancas' : 'Negras'}`;
    statusElement.className = 'status';
    
    // Actualizar FEN
    updateFEN();
}

// Actualizar la representación FEN
function updateFEN() {
    let fen = '';
    
    for (let row = 0; row < 8; row++) {
        let emptyCount = 0;
        let rowFen = '';
        
        for (let col = 0; col < 8; col++) {
            const piece = gameState.board[row][col];
            
            if (piece) {
                if (emptyCount > 0) {
                    rowFen += emptyCount.toString();
                    emptyCount = 0;
                }
                
                const pieceType = piece[1]; 
                const isWhite = piece[0] === 'w';
                
                let fenChar;
                switch(pieceType) {
                    case 'p': fenChar = 'p'; break;
                    case 'r': fenChar = 'r'; break;
                    case 'n': fenChar = 'n'; break;
                    case 'b': fenChar = 'b'; break;
                    case 'q': fenChar = 'q'; break;
                    case 'k': fenChar = 'k'; break;
                    default: fenChar = '?';
                }
                
                if (isWhite) {
                    fenChar = fenChar.toUpperCase();
                }
                
                rowFen += fenChar;
            } else {
                emptyCount++;
            }
        }
        
        if (emptyCount > 0) {
            rowFen += emptyCount.toString();
        }
        
        fen += rowFen;
        if (row < 7) {
            fen += '/';
        }
    }
    
    // Simplificación de otros campos FEN: asume enroque "KQkq" y sin peón al paso "-"
    fen += ` ${gameState.currentPlayer[0]} KQkq - 0 ${Math.floor(gameState.moveHistory.length / 2) + 1}`;
    
    document.getElementById('fen').textContent = fen;
    
    addDebugInfo(`FEN generado: ${fen}`);
    validateFEN(fen);
}

// Función para validar el formato FEN
function validateFEN(fen) {
    const parts = fen.split(' ');
    const boardPart = parts[0];
    
    const rows = boardPart.split('/');
    if (rows.length !== 8) {
        addDebugInfo(`❌ FEN INVÁLIDO: Debe tener 8 filas, tiene ${rows.length}`);
        return false;
    }
    
    for (let i = 0; i < rows.length; i++) {
        let squareCount = 0;
        for (let j = 0; j < rows[i].length; j++) {
            const char = rows[i][j];
            if ('12345678'.includes(char)) {
                squareCount += parseInt(char);
            } else if ('prnbqkPRNBQK'.includes(char)) {
                squareCount += 1;
            } else {
                addDebugInfo(`❌ FEN INVÁLIDO: Carácter inválido '${char}' en fila ${i}`);
                return false;
            }
        }
        if (squareCount !== 8) {
            addDebugInfo(`❌ FEN INVÁLIDO: Fila ${i} debe tener 8 casillas, tiene ${squareCount}`);
            return false;
        }
    }
    
    addDebugInfo(`✅ FEN válido`);
    return true;
}

// Actualizar historial de movimientos
function updateMoveHistory() {
    const moveHistoryElement = document.getElementById('moveHistory');
    moveHistoryElement.innerHTML = '';
    
    for (let i = 0; i < gameState.moveHistory.length; i += 2) {
        const moveNumber = Math.floor(i / 2) + 1;
        const whiteMove = gameState.moveHistory[i];
        const blackMove = gameState.moveHistory[i + 1];
        
        const moveElement = document.createElement('div');
        moveElement.className = 'move-number';
        moveElement.textContent = `${moveNumber}.`;
        moveHistoryElement.appendChild(moveElement);
        
        const whiteMoveElement = document.createElement('div');
        whiteMoveElement.className = 'move';
        whiteMoveElement.textContent = whiteMove || '';
        moveHistoryElement.appendChild(whiteMoveElement);
        
        if (blackMove) {
            const blackMoveElement = document.createElement('div');
            blackMoveElement.className = 'move';
            blackMoveElement.textContent = blackMove;
            moveHistoryElement.appendChild(blackMoveElement);
        }
    }
}

// --- Interacción con el Servidor (Stockfish) ---

// Obtener la mejor jugada del servidor
async function getBestMove() {
    const getMoveBtn = document.getElementById('getMoveBtn');
    const resetBtn = document.getElementById('resetBtn');
    const flipBtn = document.getElementById('flipBoardBtn');
    const undoBtn = document.getElementById('undoBtn');
    const statusElement = document.getElementById('status');
    const spinner = document.getElementById('thinkingSpinner');

    // Deshabilitar controles y mostrar spinner
    getMoveBtn.disabled = true;
    resetBtn.disabled = true;
    flipBtn.disabled = true;
    undoBtn.disabled = true;
    spinner.style.display = 'flex';
    statusElement.textContent = 'Consultando a Stockfish...';
    statusElement.className = 'status';

    try {
        const fen = document.getElementById('fen').textContent;
        
        addDebugInfo(`Solicitando mejor jugada para FEN: ${fen}`);
        
        if (!validateFEN(fen)) {
            throw new Error('FEN inválido, no se puede enviar al servidor');
        }
        
        const response = await fetch(`${SERVER_URL}/make_move`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ fen: fen })
        });
        
        addDebugInfo(`Respuesta del servidor: ${response.status} ${response.statusText}`);
        
        if (!response.ok) {
            let errorMessage = `Error HTTP: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                const errorText = await response.text();
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        addDebugInfo(`Datos recibidos: ${JSON.stringify(data)}`);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.best_move) {
            const bestMove = data.best_move;
            applyMoveFromNotation(bestMove);
            statusElement.textContent = `Stockfish jugó: ${bestMove}`;
            statusElement.className = 'status success';
            addDebugInfo(`Movimiento aplicado: ${bestMove}`);
        } else {
            // Caso donde el juego termina o no hay movimiento
            statusElement.textContent = data.status || 'Respuesta inesperada del servidor.';
            statusElement.className = 'status';
        }
        
    } catch (error) {
        console.error('Error completo:', error);
        statusElement.textContent = `Error: ${error.message}`;
        statusElement.className = 'status error';
        addDebugInfo(`ERROR: ${error.message}`);
        
        if (error.message.includes('engine') || error.message.includes('Stockfish')) {
            addDebugInfo('Intentando reiniciar el motor...');
            setTimeout(() => {
                fetch(`${SERVER_URL}/restart_engine`, { method: 'POST' })
                    .then(() => addDebugInfo('Motor reiniciado, intenta de nuevo'))
                    .catch(e => addDebugInfo(`Error reiniciando motor: ${e.message}`));
            }, 1000);
        }
    } finally {
        // Habilitar controles y ocultar spinner
        getMoveBtn.disabled = false;
        resetBtn.disabled = false;
        flipBtn.disabled = false;
        undoBtn.disabled = false;
        spinner.style.display = 'none';
        checkServerConnection();
    }
}

// --- Eventos de Botones ---

// Reiniciar el tablero
function resetBoard() {
    gameState = {
        board: Array(8).fill().map(() => Array(8).fill(null)),
        currentPlayer: 'white',
        selectedPiece: null,
        possibleMoves: [],
        moveHistory: [],
        boardFlipped: false
    };
    
    initializeBoard();
    const statusElement = document.getElementById('status');
    statusElement.textContent = 'Tablero reiniciado. Turno de las Blancas';
    statusElement.className = 'status success';
    addDebugInfo('Tablero reiniciado');
}

// Voltear el tablero (funcionalidad incompleta)
function flipBoard() {
    gameState.boardFlipped = !gameState.boardFlipped;
    addDebugInfo(`Tablero volteado: ${gameState.boardFlipped ? 'Negras' : 'Blancas'}`);
    alert("Tablero volteado. En una implementación completa, esto cambiaría la perspectiva visual.");
}

// Deshacer último movimiento (funcionalidad incompleta)
function undoMove() {
    if (gameState.moveHistory.length > 0) {
        addDebugInfo("Función de deshacer - no implementada completamente");
        alert("Función de deshacer activada. En una implementación completa, esto revertiría el último movimiento.");
    } else {
        alert("No hay movimientos para deshacer.");
    }
}


// --- Lógica de arranque ---

document.addEventListener('DOMContentLoaded', () => {
    initializeBoard();

    // Asignar eventos a los botones
    document.getElementById('getMoveBtn').addEventListener('click', getBestMove);
    document.getElementById('resetBtn').addEventListener('click', resetBoard);
    document.getElementById('flipBoardBtn').addEventListener('click', flipBoard);
    document.getElementById('undoBtn').addEventListener('click', undoMove);
});