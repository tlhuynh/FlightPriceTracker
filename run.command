#!/bin/bash

# Navigate to the project directory regardless of where the script is launched from
cd "$(dirname "$0")"

echo "Starting Flight Tracker..."
echo ""

poetry run python -m app.main

echo ""
read -p "Done. Press Enter to close..."
