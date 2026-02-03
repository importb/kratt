# Kratt

<p align="center">
  <img src="/images/example1.png" width="832" alt="Kratt Screenshot">
</p>

<p align="center">
  A lightweight, local-first desktop AI assistant for Linux, powered by <b>Ollama</b>.
</p>

---

Kratt is a simple, draggable desktop widget that provides a chat interface for your local language models. It's designed to be a minimal and convenient way to access AI assistance without relying on cloud services.

## Requirements
-   Python 3.10+
-   Fedora Linux (or another Linux distribution with standard command-line tools).
-   **Ollama** installed and running.
-   The `grep` and `find` command-line utilities must be available in your `PATH`.

### Installation & Running

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/importb/kratt.git
    cd kratt
    ```

2.  **Install the required Python packages:**
    ```sh
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3. ** Install Playwright browsers:**
    ```sh
    playwright install
    ```

4. **Pull the required Ollama models:**
    By default, Kratt uses a main model, a vision model, and an embedding model. These can be changed in the settings.
    ```sh
    ollama pull qwen2.5:7b
    ollama pull moondream:latest
    ollama pull nomic-embed-text
    ```

5. **Run the application:**
    ```sh
    python -m kratt.main
    ```

---

## Configuration

Kratt is configurable through its built-in settings dialog, which can be accessed by clicking the gear icon (⚙️) in the header.

*   **Models**: The application automatically detects and lists all models available in your local Ollama instance. You can select different models for text and vision tasks.
*   **System Prompt**: You can edit the system prompt to customize the assistant's personality, behavior, and response format.

The default hotkey is set in `kratt/config.py` and can be modified there if needed.

## License

Distributed under the MIT License. See `LICENSE` for more information.