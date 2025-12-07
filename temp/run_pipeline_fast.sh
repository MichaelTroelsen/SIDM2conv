#!/bin/bash
# Quick pipeline runner - skips WAV rendering to save time

echo "Running FAST pipeline (WAV rendering disabled)..."
echo "This will be ~10x faster"
echo""

# Set environment variable to skip WAV
export SKIP_WAV_RENDERING=1

python complete_pipeline_with_validation.py "$@"
