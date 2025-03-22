#!/bin/bash

# Script to visualize Vedic charts from test JSON files
# Usage: ./visualize_charts.sh [options]
# Options:
#   --input-json FILE    Path to input JSON file (default: tests/test_data_source/test_charts_data.json)
#   --output-dir DIR     Directory to save output files (default: test_chart_visualisation/output)
#   --format FORMAT      Output format: ascii, png, html, all (default: all)
#   --show-planets       Show planet symbols in chart (default: true)
#   --help               Show this help message

# Default values
INPUT_JSON="tests/test_data_source/test_charts_data.json"
OUTPUT_DIR="tests/test_chart_visualisation/output"
FORMAT="all"
SHOW_PLANETS="true"

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --input-json)
            INPUT_JSON="$2"
            shift
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift
            shift
            ;;
        --format)
            FORMAT="$2"
            shift
            shift
            ;;
        --show-planets)
            SHOW_PLANETS="$2"
            shift
            shift
            ;;
        --help)
            echo "Usage: ./visualize_charts.sh [options]"
            echo "Options:"
            echo "  --input-json FILE    Path to input JSON file (default: tests/test_data_source/test_charts_data.json)"
            echo "  --output-dir DIR     Directory to save output files (default: tests/test_chart_visualisation/output)"
            echo "  --format FORMAT      Output format: ascii, png, html, all (default: all)"
            echo "  --show-planets       Show planet symbols in chart (default: true)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Check if input file exists
if [ ! -f "$INPUT_JSON" ]; then
    echo "Error: Input file '$INPUT_JSON' not found!"
    exit 1
fi

# Run the Python script to generate visualizations
echo "Generating Vedic chart visualizations from $INPUT_JSON"
python tests/test_chart_visualisation/vedic_chart_visualizer.py \
    --input-json "$INPUT_JSON" \
    --output-dir "$OUTPUT_DIR" \
    --format "$FORMAT" \
    --show-planets "$SHOW_PLANETS"

echo "Visualization complete. Output files saved to $OUTPUT_DIR"
