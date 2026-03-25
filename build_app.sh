#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Mail Organizer"
APP_DIR="${SCRIPT_DIR}/${APP_NAME}.app"
CONTENTS="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS}/MacOS"
RESOURCES="${CONTENTS}/Resources"
ICON_SRC="${SCRIPT_DIR}/resources/icon.png"

echo "Building ${APP_NAME}.app..."

rm -rf "${APP_DIR}"
mkdir -p "${MACOS_DIR}" "${RESOURCES}"

# --- Generate .icns from icon.png ---
if [ -f "${ICON_SRC}" ]; then
    ICONSET="${SCRIPT_DIR}/resources/AppIcon.iconset"
    mkdir -p "${ICONSET}"
    for SIZE in 16 32 64 128 256 512; do
        sips -z ${SIZE} ${SIZE} "${ICON_SRC}" --out "${ICONSET}/icon_${SIZE}x${SIZE}.png" >/dev/null 2>&1
        DOUBLE=$((SIZE * 2))
        if [ ${DOUBLE} -le 1024 ]; then
            sips -z ${DOUBLE} ${DOUBLE} "${ICON_SRC}" --out "${ICONSET}/icon_${SIZE}x${SIZE}@2x.png" >/dev/null 2>&1
        fi
    done
    iconutil -c icns "${ICONSET}" -o "${RESOURCES}/AppIcon.icns" 2>/dev/null || true
    rm -rf "${ICONSET}"
    echo "  Icon generated."
else
    echo "  No icon.png found — app will use default icon."
fi

# --- Info.plist ---
cat > "${CONTENTS}/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Mail Organizer</string>
    <key>CFBundleDisplayName</key>
    <string>Mail Organizer</string>
    <key>CFBundleIdentifier</key>
    <string>com.mailorganizer.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

# --- Launcher script ---
cat > "${MACOS_DIR}/launcher" << LAUNCHER
#!/bin/bash
PROJECT_DIR="${SCRIPT_DIR}"
cd "\${PROJECT_DIR}"

export PATH="/usr/local/bin:/opt/homebrew/bin:\${PATH}"

if [ -f "\${PROJECT_DIR}/.venv/bin/activate" ]; then
    source "\${PROJECT_DIR}/.venv/bin/activate"
fi

# Kill any existing Streamlit on this port
lsof -ti:8501 | xargs kill -9 2>/dev/null || true

# Launch Streamlit
"\${PROJECT_DIR}/.venv/bin/streamlit" run "\${PROJECT_DIR}/mail_organizer/app.py" \\
    --server.headless true \\
    --server.port 8501 \\
    --browser.gatherUsageStats false &

STREAMLIT_PID=\$!

sleep 2
open "http://localhost:8501"

wait \${STREAMLIT_PID}
LAUNCHER

chmod +x "${MACOS_DIR}/launcher"

echo "✅ ${APP_NAME}.app built at: ${APP_DIR}"
echo "   Drag it to /Applications or your Dock."
