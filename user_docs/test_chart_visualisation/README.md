# Vedic Chart Visualization Tool

This tool visualizes Vedic birth charts in the traditional North Indian Kundali style from JSON data produced by the birth time rectification tests.

## Features

- Visualize original and rectified birth charts
- Multiple output formats: ASCII, PNG images, and HTML
- Side-by-side comparison of original and rectified charts
- Highlight changes in planetary positions

## Requirements

- Python 3.6+
- matplotlib
- numpy

## Usage

```bash
# Run with default options
./visualize_charts.sh

# Specify input JSON and output directory
./visualize_charts.sh --input-json tests/test_data_source/test_charts_data.json --output-dir ./output

# Choose specific output format
./visualize_charts.sh --format ascii
./visualize_charts.sh --format png
./visualize_charts.sh --format html
./visualize_charts.sh --format all

# Hide planet symbols in the chart
./visualize_charts.sh --show-planets false
```

## Command Line Options

- `--input-json FILE`: Path to input JSON file (default: tests/test_data_source/test_charts_data.json)
- `--output-dir DIR`: Directory to save output files (default: tests/test_chart_visualisation/output)
- `--format FORMAT`: Output format: ascii, png, html, all (default: all)
- `--show-planets`: Show planet symbols in chart (default: true)
- `--help`: Show help message

## Input JSON Format

The tool expects a JSON file with the following structure:

```json
{
  "original_birth_details": { ... },
  "original_chart": { ... },
  "rectification_details": { ... },
  "rectified_birth_details": { ... },
  "rectified_chart": { ... }
}
```

## Output Files

The tool generates the following output files:

- ASCII text files: `original_chart_ascii.txt`, `rectified_chart_ascii.txt`
- PNG images: `original_chart.png`, `rectified_chart.png`, `chart_comparison.png`
- HTML files: `original_vedic_birth_chart.html`, `rectified_vedic_birth_chart.html`, `chart_comparison.html`

## Docker Usage

To run this tool in a Docker container after running the test sequence flow:

```bash
# First, run the integration test to generate the chart data
docker-compose exec app python tests/integration/test_sequence_flow_real.py

# Then, run the visualization tool
docker-compose exec app ./tests/test_chart_visualisation/visualize_charts.sh
```
