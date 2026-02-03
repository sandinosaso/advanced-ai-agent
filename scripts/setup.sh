#!/bin/bash

# 🤖 AI Job Search Agent - Setup Script
# Modern Python dependency management with UV

set -e  # Exit on error

echo "🤖 AI Job Search Agent - Setup"
echo "================================"
echo ""

# Check if Homebrew is installed (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍺 Checking for Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "   ⚠️  Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "   ✅ Homebrew installed"
    else
        echo "   ✅ Homebrew found"
    fi
    echo ""
fi

# Check if UV is installed
echo "⚡ Checking for UV package manager..."
if ! command -v uv &> /dev/null; then
    echo "   📥 UV not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install uv
    else
        # Linux/Windows with curl
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    echo "   ✅ UV installed successfully"
else
    UV_VERSION=$(uv --version)
    echo "   ✅ UV already installed ($UV_VERSION)"
fi
echo ""

# Navigate to project root
cd "$(dirname "$0")/.." || exit

# Create virtual environment with UV
echo "🐍 Setting up Python virtual environment..."
if [ -d ".venv" ]; then
    echo "   ℹ️  Virtual environment already exists"
else
    uv venv
    echo "   ✅ Virtual environment created (.venv/)"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "   ✅ Activated"
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi
echo "   ✅ All dependencies installed"
echo ""

# Create .env file if it doesn't exist
echo "🔐 Configuring environment variables..."
if [ -f ".env" ]; then
    echo "   ℹ️  .env file already exists"
else
    cp .env.example .env
    echo "   ✅ Created .env file"
    echo "   ⚠️  IMPORTANT: Add your API keys to .env!"
fi
echo ""

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p data/vector_store
mkdir -p data/embeddings_cache
mkdir -p artifacts
echo "   ✅ data/vector_store/"
echo "   ✅ data/embeddings_cache/"
echo "   ✅ artifacts/"
echo ""

# Show environment info
echo "ℹ️  Environment Info:"
echo "   UV:     $(uv --version)"
echo "   Python: $(python --version)"
echo "   Path:   $(which python)"
echo ""

# Final instructions
echo "================================"
echo "🎉 Setup Complete!"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1️⃣  Configure API Keys and Database:"
echo "   📝 Edit: .env"
echo "   🔑 Add: OPENAI_API_KEY=your_key_here"
echo "   🗄️  Configure database settings:"
echo "      DB_HOST=127.0.0.1"
echo "      DB_PORT=3306"
echo "      DB_USER=root"
echo "      DB_PWD=your_password"
echo "      DB_NAME=crewos"
echo "      DB_ENCRYPT_KEY=your_encryption_key"
echo ""
echo "3️⃣  Run the API Server:"
echo "   🐍 source .venv/bin/activate"
echo "   ▶️  python scripts/run-dev.py"
echo ""
echo "   💡 Or use UV directly (no activation needed):"
echo "   ▶️  uv run python scripts/run-dev.py"
echo ""
echo "4️⃣  Configure VSCode:"
echo "   ⌨️  Press: Cmd+Shift+P"
echo "   🔍 Type: 'Python: Select Interpreter'"
echo "   ✅ Choose: ./.venv/bin/python"
echo ""
echo "5️⃣  Start Building:"
echo "   💬 Ask: 'Help me implement Phase 1 - Simple Job Scraper'"
echo ""
echo "⚡ UV Quick Commands:"
echo "   📦 uv pip install <package>  - Install package"
echo "   📋 uv pip list               - List packages"
echo "   🔄 uv pip install -U <pkg>   - Update package"
echo "   ▶️  uv run <command>          - Run in venv"
echo ""
echo "Happy coding! 🚀"
