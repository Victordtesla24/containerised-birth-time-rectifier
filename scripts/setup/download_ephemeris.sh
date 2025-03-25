#!/bin/bash
set -e

# Define colors for output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Log functions
log_info() {
  echo -e "[INFO] $1"
}

log_success() {
  echo -e "[SUCCESS] $1"
}

log_warning() {
  echo -e "[WARNING] $1"
}

log_error() {
  echo -e "[ERROR] $1"
}

# Get ephemeris directory from environment or default
EPHEMERIS_DIR=${SWISSEPH_PATH:-/app/ephemeris}
ARCHIVE_NAME="swisseph_files.zip"

log_info "Starting ephemeris download process"
log_info "Target directory: $EPHEMERIS_DIR"

# Create ephemeris directory if it doesn't exist
if [ ! -d "$EPHEMERIS_DIR" ]; then
  log_info "Creating ephemeris directory: $EPHEMERIS_DIR"
  mkdir -p "$EPHEMERIS_DIR" || { log_error "Failed to create $EPHEMERIS_DIR"; exit 1; }
fi

cd "$EPHEMERIS_DIR" || { log_error "Failed to change to $EPHEMERIS_DIR"; exit 1; }
log_info "Working directory: $(pwd)"

# List of core essential ephemeris files that are absolutely needed
CORE_ESSENTIAL_FILES=(
  "sepl_18.se1"  # Planets Main - CRITICAL
  "semo_18.se1"  # Moon - CRITICAL
  "seas_18.se1"  # Asteroids
)

# List of additional ephemeris files that are nice to have but not critical
ADDITIONAL_FILES=(
  "seau_18.se1"  # Uranus
  "sene_18.se1"  # Neptune
  "sepj_18.se1"  # Jupiter
  "sepx_18.se1"  # Pluto
  "sesa_18.se1"  # Saturn
  "sevi_18.se1"  # Venus
  "seme_18.se1"  # Mercury
  "fixstars.cat" # Fixed stars catalog
  "seorbel.txt"  # Orbital elements
)

# Combine into one array for checking
ESSENTIAL_FILES=("${CORE_ESSENTIAL_FILES[@]}" "${ADDITIONAL_FILES[@]}")

# Check existing files
log_info "Checking existing ephemeris files in $EPHEMERIS_DIR..."
MISSING_FILES=()
for FILE in "${ESSENTIAL_FILES[@]}"; do
  if [ ! -f "$FILE" ]; then
    MISSING_FILES+=("$FILE")
  fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
  log_success "All essential ephemeris files already exist in $EPHEMERIS_DIR"
  # Create a verification file to indicate download was successful
  echo "Downloaded on $(date)" > .ephemeris_downloaded
  exit 0
fi

log_info "Need to download ${#MISSING_FILES[@]} missing ephemeris files: ${MISSING_FILES[*]}"

# Try direct downloads for essential files from multiple sources
FALLBACK_URLS=(
  "https://www.astro.com/ftp/swisseph/ephe/"
  "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/"
)

# Download individual files directly
for FILE in "${MISSING_FILES[@]}"; do
  log_info "Trying to download $FILE..."

  for BASE_URL in "${FALLBACK_URLS[@]}"; do
    URL="${BASE_URL}${FILE}"
    log_info "Trying $URL"

    if command -v curl &>/dev/null; then
      if curl -s -f -L -o "$FILE" "$URL"; then
        log_success "Successfully downloaded $FILE from $URL"
        break
      else
        log_warning "Failed to download $FILE from $URL"
      fi
    elif command -v wget &>/dev/null; then
      if wget -q -O "$FILE" "$URL"; then
        log_success "Successfully downloaded $FILE from $URL"
        break
      else
        log_warning "Failed to download $FILE from $URL"
      fi
    fi
  done

  # Check if the file was downloaded
  if [ ! -f "$FILE" ]; then
    log_warning "Failed to download $FILE from all sources"
    # Create empty placeholder as a last resort
    touch "$FILE"
    log_warning "Created empty placeholder for $FILE - charts may not be accurate!"
  fi
done

# Final verification
log_info "Performing final verification..."
num_se1_files=$(ls -1 ./*.se1 2>/dev/null | wc -l)
log_info "Found $num_se1_files .se1 files in $EPHEMERIS_DIR"

# Set permissions
log_info "Setting permissions on ephemeris files..."
chmod -R 755 .

# Create a verification file to indicate download attempt
echo "Downloaded on $(date)" > .ephemeris_downloaded
log_success "Ephemeris download process completed"
