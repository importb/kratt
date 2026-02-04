#!/bin/bash
set -e

PROJECT_ROOT=$(pwd)
SERVICE_NAME="kratt"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "--- Starting Kratt Setup ---"

# 1. Create virtual environment
echo "Creating virtual environment in .venv..."
python3 -m venv .venv
source .venv/bin/activate

# 2. Install requirements
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Install Playwright
echo "Installing Playwright browsers..."
playwright install

# 4. Systemd Auto-startup
read -p "Do you want to create a systemd user service for automatic startup? (y/N): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "Creating systemd user service..."

    mkdir -p "$SYSTEMD_USER_DIR"

    cat <<EOF > "$SYSTEMD_USER_DIR/$SERVICE_NAME.service"
[Unit]
Description=Kratt AI Assistant
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/.venv/bin/python -m kratt.main
Restart=on-failure
Environment=PYTHONPATH=$PROJECT_ROOT
# Ensures the app can connect to the X11/Wayland display
Environment=DISPLAY=:0

[Install]
WantedBy=graphical-session.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME.service"

    echo "Service created and enabled."
    echo "To start it now, run: systemctl --user start $SERVICE_NAME"
fi

echo "--- Setup Complete! ---"
echo "To run Kratt manually: source .venv/bin/activate && python3 -m kratt.main"