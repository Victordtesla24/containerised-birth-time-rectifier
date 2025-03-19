#!/bin/bash

# Script to download Swiss Ephemeris data
# This data is required for precise astrological calculations

# Set the ephemeris directory
EPHEMERIS_DIR="/app/ephemeris"

# Create the directory if it doesn't exist
mkdir -p "$EPHEMERIS_DIR"
if [ ! -d "$EPHEMERIS_DIR" ]; then
    echo "ERROR: Failed to create ephemeris directory: $EPHEMERIS_DIR"
    exit 1
fi

# Use GitHub as source for ephemeris files
echo "Downloading Swiss Ephemeris files from GitHub..."

# Base URL for the Swiss Ephemeris files on GitHub
GITHUB_BASE_URL="https://github.com/aloistr/swisseph/raw/master/ephe"

# List of files to download - comprehensive set for accurate calculations
FILES=(
  # Main planetary ephemeris files (1800-2399)
  "sepl_18.se1"  # Planets
  "semo_18.se1"  # Moon
  "seas_18.se1"  # Asteroids
  "sema_18.se1"  # Mars
  "semn_18.se1"  # Minor planets
  "sejp_18.se1"  # Jupiter
  "sesa_18.se1"  # Saturn
  "seur_18.se1"  # Uranus
  "sene_18.se1"  # Neptune
  "sepl_18.se1"  # Pluto

  # Additional required files
  "seleapsec.txt"  # Leap seconds
  "senamnut.txt"   # Nutation data

  # Fixed stars
  "fixstars.cat"   # Fixed stars catalog
  "sefstars.txt"   # Fixed stars data

  # Asteroid files - these might be large, only download if needed
  # "seasm54.se1"    # Asteroid main belt
  # "seastm54.se1"   # Asteroid Chiron and Pholus
)

# Download each file
DOWNLOAD_ERROR=false

for file in "${FILES[@]}"; do
  if [ ! -f "$EPHEMERIS_DIR/$file" ] || [ ! -s "$EPHEMERIS_DIR/$file" ]; then
    echo "Downloading $file..."
    curl -s -L -o "$EPHEMERIS_DIR/$file" "$GITHUB_BASE_URL/$file"

    # Check if download was successful
    if [ $? -eq 0 ] && [ -s "$EPHEMERIS_DIR/$file" ]; then
      # Check if file is not an HTML error page
      if grep -q "<!DOCTYPE html" "$EPHEMERIS_DIR/$file"; then
        echo "ERROR: Downloaded HTML instead of ephemeris data for $file"
        DOWNLOAD_ERROR=true
      else
        echo "Successfully downloaded $file"
      fi
    else
      echo "ERROR: Failed to download $file"
      DOWNLOAD_ERROR=true
    fi
  else
    echo "File $file already exists"
  fi
done

# Check if we have the minimum required files for calculations
CRITICAL_FILES=("sepl_18.se1" "semo_18.se1" "seas_18.se1")
MISSING_CRITICAL=false

for file in "${CRITICAL_FILES[@]}"; do
  if [ ! -f "$EPHEMERIS_DIR/$file" ] || [ ! -s "$EPHEMERIS_DIR/$file" ] || grep -q "<!DOCTYPE html" "$EPHEMERIS_DIR/$file"; then
    echo "ERROR: Critical file $file is missing or invalid!"
    MISSING_CRITICAL=true
  fi
done

if [ "$MISSING_CRITICAL" = true ]; then
  echo "ERROR: Some critical ephemeris files are missing - chart calculations cannot proceed"

  # Try alternative source - direct download from SwissEph
  echo "Trying alternative source for ephemeris files..."

  # Download a pre-packaged ephemeris archive
  ARCHIVE_NAME="ephe.zip"
  ARCHIVE_URL="https://github.com/aloistr/swisseph/archive/refs/heads/master.zip"

  cd /tmp
  curl -s -L -o "$ARCHIVE_NAME" "$ARCHIVE_URL"

  if [ $? -eq 0 ] && [ -s "$ARCHIVE_NAME" ]; then
    echo "Successfully downloaded archive"

    # Install unzip if not available
    which unzip >/dev/null 2>&1 || apt-get update && apt-get install -y unzip

    # Extract the archive
    unzip -q "$ARCHIVE_NAME"

    # Copy ephemeris files to the target directory
    cp -v swisseph-master/ephe/*.se1 "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .se1 files found"
    cp -v swisseph-master/ephe/*.txt "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .txt files found"
    cp -v swisseph-master/ephe/*.cat "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .cat files found"

    # Clean up
    rm -rf "$ARCHIVE_NAME" swisseph-master

    # Check again for critical files
    MISSING_CRITICAL=false
    for file in "${CRITICAL_FILES[@]}"; do
      if [ ! -f "$EPHEMERIS_DIR/$file" ] || [ ! -s "$EPHEMERIS_DIR/$file" ] || grep -q "<!DOCTYPE html" "$EPHEMERIS_DIR/$file"; then
        echo "ERROR: Critical file $file is still missing or invalid after alternative download!"
        MISSING_CRITICAL=true
      fi
    done

    if [ "$MISSING_CRITICAL" = true ]; then
      echo "ERROR: Failed to download ephemeris files from alternative source"
      exit 1
    else
      echo "Successfully downloaded ephemeris files from alternative source"
    fi
  else
    echo "ERROR: Failed to download archive"
    exit 1
  fi
else
  echo "All critical ephemeris files are present."
fi

# Set permissions
echo "Setting permissions..."
chmod -R 755 "$EPHEMERIS_DIR"

# Final verification of ephemeris files
num_files=$(ls "$EPHEMERIS_DIR"/*.se1 2>/dev/null | wc -l)
if [ "$num_files" -lt 3 ]; then
  echo "ERROR: Insufficient ephemeris files found - chart calculations may fail"
  exit 1
fi

echo "Swiss Ephemeris files are ready."

# Check if there were any download errors
if [ "$DOWNLOAD_ERROR" = true ]; then
  echo "WARNING: Some files failed to download. The application may still work if critical files were obtained."
  exit 0
fi

exit 0
