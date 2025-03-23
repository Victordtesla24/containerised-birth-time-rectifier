#!/bin/bash
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

echo -e "${BLUE}[INFO]${NC} Checking for Python 3 installation..."

# Check if Python 3 is already installed
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Python 3 is already installed: $(python3 --version)"
    exit 0
fi

echo -e "${YELLOW}[WARNING]${NC} Python 3 not found. Installing..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} Homebrew not found. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH if needed
    if [[ $(uname -m) == "arm64" ]]; then
        echo -e "${BLUE}[INFO]${NC} Adding Homebrew to PATH for Apple Silicon..."
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo -e "${BLUE}[INFO]${NC} Adding Homebrew to PATH for Intel Mac..."
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

# Install Python 3
echo -e "${BLUE}[INFO]${NC} Installing Python 3 using Homebrew..."
brew install python@3.11

# Verify installation
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Python 3 installed successfully: $(python3 --version)"

    # Install virtualenv
    echo -e "${BLUE}[INFO]${NC} Installing virtualenv..."
    python3 -m pip install --user virtualenv

    echo -e "${GREEN}[SUCCESS]${NC} Setup complete! You may need to restart your terminal."
    echo -e "${YELLOW}[NOTE]${NC} You can now run the dependency test script:"
    echo -e "       ./scripts/setup/test_dependencies.sh"
else
    echo -e "${RED}[ERROR]${NC} Failed to install Python 3. Please install manually from python.org"
    exit 1
fi
