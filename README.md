# Chess_GUI con Stockfish

Una sencilla interfaz de ajedrez basada en la web que utiliza el motor de ajedrez Stockfish para proporcionar análisis y sugerencias de jugadas. El frontend está construido con HTML, CSS y JavaScript, y el backend es un servidor Flask en Python que se comunica con el motor Stockfish.

## Características

-   **Interfaz Gráfica de Ajedrez:** Un tablero de ajedrez interactivo creado con HTML/CSS y JavaScript.
-   **Motor Stockfish:** Integración con el motor de ajedrez Stockfish para calcular la mejor jugada desde cualquier posición.
-   **Comunicación Frontend-Backend:** El frontend se comunica con un servidor local Flask para obtener los movimientos de Stockfish.
-   **Visualización de FEN:** Muestra la notación FEN de la posición actual del tablero.
-   **Historial de Movimientos:** Registra y muestra los movimientos de la partida.

## Requisitos Previos

-   Python 3.6+
-   El motor de ajedrez [Stockfish](https://stockfishchess.org/download/). Deberás descargar el ejecutable adecuado para tu sistema operativo.
-   Un navegador web moderno.

## Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone <URL-del-repositorio>
    cd Chess_GUI
    ```

2.  **Crea y activa un entorno virtual (recomendado):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instala las dependencias de Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura la ruta de Stockfish:**
    -   Abre el archivo `server.py`.
    -   Localiza la variable `STOCKFISH_PATH` y asegúrate de que la ruta apunte a la ubicación del ejecutable de Stockfish que descargaste.
    ```python
    # Ejemplo:
    STOCKFISH_PATH = "/ruta/a/tu/stockfish"
    ```

## Uso

1.  **Inicia el servidor de Flask:**
    Ejecuta el siguiente comando en la raíz del proyecto:
    ```bash
    python3 server.py
    ```
    El servidor se iniciará en `http://127.0.0.1:5000`.

2.  **Abre la interfaz de usuario:**
    Abre el archivo `chess_interface.html` en tu navegador web. Puedes hacerlo haciendo doble clic en el archivo o abriéndolo desde el navegador.

    ¡Y listo! Ahora puedes jugar en el tablero. Usa el botón "Mejor Jugada" para pedirle a Stockfish que te muestre el mejor movimiento.