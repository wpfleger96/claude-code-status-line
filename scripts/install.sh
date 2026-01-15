#!/usr/bin/env bash

set -e

PACKAGE_NAME="claude-code-statusline"

echo "Installing $PACKAGE_NAME..."
echo ""

install_with_uv() {
    echo "Found uv. Installing with uv tool..."
    uv tool install "$PACKAGE_NAME"
    return $?
}

install_with_pipx() {
    echo "Found pipx. Installing with pipx..."
    pipx install "$PACKAGE_NAME"
    return $?
}

if command -v uv &> /dev/null; then
    if ! install_with_uv; then
        echo ""
        echo "Error: uv installation failed"
        exit 1
    fi
elif command -v pipx &> /dev/null; then
    if ! install_with_pipx; then
        echo ""
        echo "Error: pipx installation failed"
        exit 1
    fi
else
    echo "Error: Neither uv nor pipx found"
    echo ""
    echo "Please install one of:"
    echo "  uv:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  pipx: python3 -m pip install --user pipx"
    exit 1
fi

echo ""
echo "Package installed successfully!"
echo ""
echo "Configuring Claude Code..."

if ! claude-statusline install --yes; then
    echo ""
    echo "Error: Configuration failed"
    echo "You can try manually running: claude-statusline install"
    exit 1
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code or start a new session"
echo "2. The statusline should appear automatically"
echo "3. Customize via ~/.config/claude-statusline/config.yaml"
echo ""
echo "For more information, visit:"
echo "  https://github.com/wpfleger96/claude-code-status-line"
