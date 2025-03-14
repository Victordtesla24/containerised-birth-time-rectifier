#!/bin/bash

# Script to download Swiss Ephemeris data
# This data is required for precise astrological calculations

# Set the ephemeris directory
EPHEMERIS_DIR="/app/ephemeris"

# Create the directory if it doesn't exist
mkdir -p "$EPHEMERIS_DIR"

# Download the Swiss Ephemeris files
# Main ephemeris files
echo "Downloading Swiss Ephemeris files..."

# List of files to download
FILES=(
  "seas_18.se1"  # Main planets 1800-2399
  "semo_18.se1"  # Moon 1800-2399
  "sepl_18.se1"  # Planets 1800-2399
  "se00010s.cat" # Fixed stars catalog
  "seasm54.se1"  # Asteroid main belt
  "seastm54.se1" # Asteroid Chiron and Pholus
  "seas_ml.se1"  # Extra asteroid data
  "sepl.se1"     # Planet positions
  "semo.se1"     # Moon positions
  "seleapsec.txt" # Leap seconds
  "senamnut.txt"  # Nutation data
)

# URL for Swiss Ephemeris files
BASE_URL="https://www.astro.com/ftp/swisseph/ephe"

# Download each file
for file in "${FILES[@]}"; do
  if [ ! -f "$EPHEMERIS_DIR/$file" ]; then
    echo "Downloading $file..."
    curl -s -o "$EPHEMERIS_DIR/$file" "$BASE_URL/$file"

    # Check if download was successful
    if [ $? -eq 0 ]; then
      echo "Successfully downloaded $file"
    else
      echo "Failed to download $file"
    fi
  else
    echo "File $file already exists"
  fi
done

# Set permissions
echo "Setting permissions..."
chmod -R 755 "$EPHEMERIS_DIR"

echo "Swiss Ephemeris files are ready."
