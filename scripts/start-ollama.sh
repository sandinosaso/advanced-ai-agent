#!/bin/bash

# Script to start Ollama server on macOS
# This script checks if Ollama is installed and starts the server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Ollama Server${NC}\n"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed${NC}\n"
    echo -e "${YELLOW}To install Ollama:${NC}"
    echo "  1. Visit https://ollama.com/download and download the macOS installer"
    echo "  2. Or use Homebrew:"
    echo "     brew install ollama"
    echo ""
    echo -e "${YELLOW}After installation, run this script again.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ollama is installed${NC}"

# Check if Ollama is already running
if pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama appears to be already running${NC}"
    echo ""
    echo "To check Ollama status:"
    echo "  ollama list"
    echo ""
    echo "To stop Ollama:"
    echo "  pkill ollama"
    echo ""
    read -p "Do you want to restart Ollama? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Stopping existing Ollama process...${NC}"
        pkill ollama || true
        sleep 2
    else
        echo -e "${GREEN}Keeping existing Ollama process running${NC}"
        exit 0
    fi
fi

# Check if Ollama server is responding
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama server is already responding on http://localhost:11434${NC}"
    echo ""
    echo "Available models:"
    ollama list 2>/dev/null || echo "  (No models installed yet)"
    echo ""
    echo "To pull a model:"
    echo "  ollama pull llama3"
    echo "  ollama pull codellama"
    echo "  ollama pull mistral"
    exit 0
fi

# Start Ollama server
echo -e "${BLUE}Starting Ollama server...${NC}"
echo ""

# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!

# Wait a moment for server to start
sleep 3

# Check if process is still running
if ! ps -p $OLLAMA_PID > /dev/null; then
    echo -e "${RED}❌ Failed to start Ollama server${NC}"
    echo ""
    echo "Try starting manually:"
    echo "  ollama serve"
    exit 1
fi

# Verify server is responding
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Ollama server started successfully!${NC}"
        echo ""
        echo "Server running on: http://localhost:11434"
        echo "Process ID: $OLLAMA_PID"
        echo ""
        echo "Available models:"
        ollama list 2>/dev/null || echo "  (No models installed yet)"
        echo ""
        echo -e "${YELLOW}💡 Next steps:${NC}"
        echo "  1. Pull a model: ollama pull llama3"
        echo "  2. Configure .env: LLM_PROVIDER=ollama"
        echo "  3. Start your application"
        echo ""
        echo -e "${YELLOW}To stop Ollama:${NC}"
        echo "  pkill ollama"
        echo "  or"
        echo "  kill $OLLAMA_PID"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

echo -e "${RED}❌ Ollama server started but is not responding${NC}"
echo ""
echo "The server process is running (PID: $OLLAMA_PID) but not responding to requests."
echo "Check logs for errors:"
echo "  tail -f ~/.ollama/logs/server.log"
exit 1
