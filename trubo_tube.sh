#!/bin/bash

# Define paths to Python scripts
SCRIPT1="0-process_document.py"
SCRIPT2="1-get_YT_videos.py"
SCRIPT3="2-process_videos.py"
SCRIPT4="3-generate_audio.py"
SCRIPT5="4-edit_video.py"

# Function to run a script and check if it succeeded
run_script() {
    echo "Running $1..."
    python3 "$1"
    if [ $? -ne 0 ]; then
        echo "❌ Error: $1 failed. Stopping execution."
        exit 1
    fi
    echo "✅ $1 completed successfully."
}

# Run scripts in sequence
run_script "$SCRIPT1"
run_script "$SCRIPT2"
run_script "$SCRIPT3"
run_script "$SCRIPT4"
run_script "$SCRIPT5"

echo "🎉 All scripts ran successfully!"
