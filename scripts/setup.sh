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

# Navigate to backend directory
cd "$(dirname "$0")/../backend" || exit

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
uv pip install -r requirements.txt
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
mkdir -p data/chroma_db
mkdir -p data/checkpoints
mkdir -p data/logs
echo "   ✅ data/chroma_db/"
echo "   ✅ data/checkpoints/"
echo "   ✅ data/logs/"
echo ""

# Test the setup
echo "🧪 Testing setup..."
python main.py
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
echo "1️⃣  Configure API Keys:"
echo "   📝 Edit: backend/.env"
echo "   🔑 Add: OPENAI_API_KEY=your_key_here"
echo "   🔑 Add: FIRECRAWL_API_KEY=your_key_here"
echo ""
echo "2️⃣  Configure Your Profile:"
echo "   📝 Edit: backend/config/config.yaml"
echo "   👤 Add your skills, target country, preferences"
echo ""
echo "3️⃣  Run the Agent:"
echo "   📂 cd backend"
echo "   🐍 source .venv/bin/activate"
echo "   ▶️  python main.py"
echo ""
echo "   💡 Or use UV directly (no activation needed):"
echo "   ▶️  uv run python main.py"
echo ""
echo "4️⃣  Configure VSCode:"
echo "   ⌨️  Press: Cmd+Shift+P"
echo "   🔍 Type: 'Python: Select Interpreter'"
echo "   ✅ Choose: ./backend/.venv/bin/python"
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
