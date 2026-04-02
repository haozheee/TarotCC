#!/usr/bin/env bash
set -euo pipefail

# Detect project directory (where this script lives)
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing TarotCC..."
echo "Project directory: $PROJECT_DIR"

# 1. Set up conda environment
if conda info --envs 2>/dev/null | grep -q "divination"; then
    echo "Conda environment 'divination' already exists, skipping creation."
else
    echo "Creating conda environment 'divination' (Python 3.12)..."
    conda create -n divination python=3.12 -y
fi

echo "Installing Python dependencies..."
conda run -n divination pip install Pillow rich

# 2. Generate and install the global slash command
COMMANDS_DIR="$HOME/.claude/commands"
mkdir -p "$COMMANDS_DIR"

echo "Generating global /tarot command..."
sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$PROJECT_DIR/commands/tarot.md" > "$COMMANDS_DIR/tarot.md"

echo ""
echo "Done! You can now use /tarot in Claude Code from any directory."
echo "Example: /tarot What does my career look like?"
