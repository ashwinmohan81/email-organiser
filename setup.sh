#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

echo "==================================="
echo "  Mail Organizer — Setup"
echo "==================================="
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it from https://python.org or via Homebrew:"
    echo "   brew install python"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Using ${PYTHON_VERSION}"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Dependencies installed."

# Copy .env if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env from template — edit it to add your API keys."
fi

# Create tokens directory
mkdir -p tokens

# Check for credentials.json
if [ ! -f "credentials.json" ]; then
    echo ""
    echo "⚠️  Missing credentials.json!"
    echo "   1. Go to https://console.cloud.google.com"
    echo "   2. Create a project (or select existing)"
    echo "   3. Enable the Gmail API"
    echo "   4. Go to Credentials → Create OAuth 2.0 Client ID (Desktop app)"
    echo "   5. Download the JSON and save it as: ${SCRIPT_DIR}/credentials.json"
    echo ""
fi

# Build macOS app
echo "Building macOS app..."
bash build_app.sh

echo ""
echo "==================================="
echo "  ✅ Setup complete!"
echo "==================================="
echo ""
echo "  To start: double-click 'Mail Organizer.app'"
echo "  Or run:   source .venv/bin/activate && streamlit run mail_organizer/app.py"
echo ""
