#!/usr/bin/env bash

set -e

PACKAGE_NAME="claude-code-statusline"
CONFIG_DIR="$HOME/.config/claude-statusline"

echo "Uninstalling $PACKAGE_NAME..."
echo ""

PURGE=0
if [ "$1" = "--purge" ]; then
    PURGE=1
fi

if command -v claude-statusline &> /dev/null; then
    echo "Removing statusLine configuration..."
    if claude-statusline uninstall; then
        echo ""
    else
        echo "Warning: Failed to remove statusLine configuration"
        echo "You may need to manually edit ~/.claude/settings.json"
        echo ""
    fi
else
    echo "claude-statusline command not found"
    echo "Skipping configuration cleanup"
    echo ""
fi

if command -v uv &> /dev/null && uv tool list 2>/dev/null | grep -q "$PACKAGE_NAME"; then
    echo "Uninstalling package with uv..."
    uv tool uninstall "$PACKAGE_NAME"
    echo "✓ Package uninstalled"
elif command -v pipx &> /dev/null && pipx list 2>/dev/null | grep -q "$PACKAGE_NAME"; then
    echo "Uninstalling package with pipx..."
    pipx uninstall "$PACKAGE_NAME"
    echo "✓ Package uninstalled"
else
    echo "Package not found in uv or pipx"
fi

if [ $PURGE -eq 1 ] && [ -d "$CONFIG_DIR" ]; then
    echo ""
    echo "Removing config directory at $CONFIG_DIR..."
    rm -rf "$CONFIG_DIR"
    echo "✓ Config directory removed"
elif [ -d "$CONFIG_DIR" ]; then
    echo ""
    echo "Config directory preserved at $CONFIG_DIR"
    echo "To remove it, run: rm -rf $CONFIG_DIR"
    echo "Or use: ./uninstall.sh --purge"
fi

echo ""
echo "Uninstallation complete!"
echo ""
echo "Note: Backup files in ~/.claude/*.backup.* have been preserved"
