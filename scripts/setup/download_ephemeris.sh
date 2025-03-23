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
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Get ephemeris directory from environment or default
EPHEMERIS_DIR=${SWISSEPH_PATH:-/app/ephemeris}
ARCHIVE_NAME="swisseph_files.zip"
GITHUB_BASE_URL="https://github.com/aloistr/swisseph/raw/master/ephe"

# Create ephemeris directory if it doesn't exist
if [ ! -d "$EPHEMERIS_DIR" ]; then
  log_info "Creating ephemeris directory: $EPHEMERIS_DIR"
  mkdir -p "$EPHEMERIS_DIR" || { log_error "Failed to create $EPHEMERIS_DIR"; exit 1; }
fi

cd "$EPHEMERIS_DIR" || { log_error "Failed to change to $EPHEMERIS_DIR"; exit 1; }

# List of essential ephemeris files
ESSENTIAL_FILES=(
  "seas_18.se1"  # Asteroids
  "semo_18.se1"  # Moon
  "sepl_18.se1"  # Planets
  "seau_18.se1"  # Uranus
  "sene_18.se1"  # Neptune
  "sepj_18.se1"  # Jupiter
  "sepx_18.se1"  # Pluto
  "sepl_18.se1"  # Planets Main
  "sesa_18.se1"  # Saturn
)

# Check existing files
log_info "Checking existing ephemeris files..."
MISSING_FILES=()
for FILE in "${ESSENTIAL_FILES[@]}"; do
  if [ ! -f "$FILE" ]; then
    MISSING_FILES+=("$FILE")
  fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
  log_success "All essential ephemeris files already exist"
  exit 0
fi

log_info "Need to download ${#MISSING_FILES[@]} missing ephemeris files"

# Try direct download first
log_info "Trying direct file downloads..."
SUCCESS=true

for FILE in "${MISSING_FILES[@]}"; do
  URL="$GITHUB_BASE_URL/$FILE"
  log_info "Downloading $FILE from $URL"

  if command -v curl &>/dev/null; then
    if ! curl -s -f -L -o "$FILE" "$URL"; then
      log_warning "Failed to download $FILE using curl"
      SUCCESS=false
      break
    fi
  elif command -v wget &>/dev/null; then
    if ! wget -q -O "$FILE" "$URL"; then
      log_warning "Failed to download $FILE using wget"
      SUCCESS=false
      break
    fi
  else
    log_error "Neither curl nor wget is available"
    SUCCESS=false
    break
  fi
done

# If individual downloads failed, try archive approach
if [ "$SUCCESS" = false ]; then
  log_info "Direct downloads failed. Trying archive download..."

  # Try alternative source - direct download from SwissEph
  if [ -f "$ARCHIVE_NAME" ]; then
    rm "$ARCHIVE_NAME"
  fi

  ARCHIVE_URL="https://github.com/aloistr/swisseph/archive/refs/heads/master.zip"

  if command -v curl &>/dev/null; then
    curl -s -L -o "$ARCHIVE_NAME" "$ARCHIVE_URL" || { log_error "Failed to download archive with curl"; exit 1; }
  elif command -v wget &>/dev/null; then
    wget -q -O "$ARCHIVE_NAME" "$ARCHIVE_URL" || { log_error "Failed to download archive with wget"; exit 1; }
  else
    log_error "Neither curl nor wget is available"
    exit 1
  fi

  # Unzip the archive
  if command -v unzip &>/dev/null; then
    unzip -q "$ARCHIVE_NAME" || { log_error "Failed to unzip archive"; exit 1; }
  else
    log_error "unzip command not found"
    exit 1
  fi

  # Copy all relevant files
  log_info "Copying ephemeris files from archive..."
    cp -v swisseph-master/ephe/*.se1 "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .se1 files found"
    cp -v swisseph-master/ephe/*.txt "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .txt files found"
    cp -v swisseph-master/ephe/*.cat "$EPHEMERIS_DIR/" 2>/dev/null || echo "No .cat files found"

    # Clean up
  log_info "Cleaning up temporary files..."
    rm -rf "$ARCHIVE_NAME" swisseph-master
fi

# Verify if all required files are now present
STILL_MISSING=()
for FILE in "${ESSENTIAL_FILES[@]}"; do
  if [ ! -f "$FILE" ]; then
    STILL_MISSING+=("$FILE")
      fi
    done

if [ ${#STILL_MISSING[@]} -eq 0 ]; then
  log_success "All essential ephemeris files successfully downloaded!"
  exit 0
else
  log_error "Some ephemeris files are still missing: ${STILL_MISSING[*]}"

  # Try the fallback source using direct package URLs
  log_info "Trying fallback download from comprehensive sources..."

  # Comprehensive Swiss Ephemeris package URL
  FALLBACK_URL="https://www.astro.com/ftp/swisseph/ephe/se_ephe.zip"
  FALLBACK_ARCHIVE="se_ephe.zip"

  if command -v curl &>/dev/null; then
    curl -s -L -o "$FALLBACK_ARCHIVE" "$FALLBACK_URL" || { log_error "Failed to download fallback archive"; exit 1; }
  elif command -v wget &>/dev/null; then
    wget -q -O "$FALLBACK_ARCHIVE" "$FALLBACK_URL" || { log_error "Failed to download fallback archive"; exit 1; }
  fi

  # Unzip the fallback archive
  if command -v unzip &>/dev/null; then
    unzip -q -o "$FALLBACK_ARCHIVE" || { log_error "Failed to unzip fallback archive"; exit 1; }
  fi

  # Clean up
  rm -f "$FALLBACK_ARCHIVE"

  # Final verification
  FINAL_MISSING=()
  for FILE in "${ESSENTIAL_FILES[@]}"; do
    if [ ! -f "$FILE" ]; then
      FINAL_MISSING+=("$FILE")
    fi
  done

  if [ ${#FINAL_MISSING[@]} -eq 0 ]; then
    log_success "All essential ephemeris files successfully downloaded through fallback source!"
    exit 0
  else
    log_error "Failed to download all required ephemeris files. Still missing: ${FINAL_MISSING[*]}"
    exit 1
  fi
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
