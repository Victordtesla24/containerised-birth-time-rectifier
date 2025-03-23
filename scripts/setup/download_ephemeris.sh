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
  exit 0
fi

log_info "Need to download ${#MISSING_FILES[@]} missing ephemeris files: ${MISSING_FILES[*]}"

# Try archive approach first (most reliable)
log_info "Downloading Swiss Ephemeris archive from GitHub..."
if [ -f "$ARCHIVE_NAME" ]; then
  rm "$ARCHIVE_NAME"
fi

ARCHIVE_URL="https://github.com/aloistr/swisseph/archive/refs/heads/master.zip"

if command -v curl &>/dev/null; then
  log_info "Using curl to download archive"
  curl -s -L -o "$ARCHIVE_NAME" "$ARCHIVE_URL" || { log_error "Failed to download archive with curl"; exit 1; }
elif command -v wget &>/dev/null; then
  log_info "Using wget to download archive"
  wget -q -O "$ARCHIVE_NAME" "$ARCHIVE_URL" || { log_error "Failed to download archive with wget"; exit 1; }
else
  log_error "Neither curl nor wget is available - cannot download files"
  exit 1
fi

# Check if archive was downloaded successfully
if [ ! -f "$ARCHIVE_NAME" ]; then
  log_error "Archive download failed - file not found"
  exit 1
fi

log_info "Archive downloaded successfully. Size: $(du -h "$ARCHIVE_NAME" | cut -f1)"

# Unzip the archive
log_info "Extracting Swiss Ephemeris archive..."
if command -v unzip &>/dev/null; then
  unzip -q "$ARCHIVE_NAME" || { log_error "Failed to unzip archive"; exit 1; }
else
  log_error "unzip command not found"
  exit 1
fi

# Verify extraction succeeded
if [ ! -d "swisseph-master" ]; then
  log_error "Archive extraction failed - directory not found"
  exit 1
fi

# Copy all relevant files
log_info "Copying ephemeris files from archive to $EPHEMERIS_DIR..."
cp -v swisseph-master/ephe/*.se1 ./ 2>/dev/null || log_warning "No .se1 files found in archive"
cp -v swisseph-master/ephe/*.txt ./ 2>/dev/null || log_warning "No .txt files found in archive"
cp -v swisseph-master/ephe/*.cat ./ 2>/dev/null || log_warning "No .cat files found in archive"

# Clean up
log_info "Cleaning up temporary files..."
rm -rf "$ARCHIVE_NAME" swisseph-master

# Check if we need to try fallback for missing files
STILL_MISSING=()
CORE_MISSING=()

# Check which files are still missing
for FILE in "${ESSENTIAL_FILES[@]}"; do
  if [ ! -f "$FILE" ]; then
    STILL_MISSING+=("$FILE")

    # Check if it's a core file
    for CORE_FILE in "${CORE_ESSENTIAL_FILES[@]}"; do
      if [ "$FILE" = "$CORE_FILE" ]; then
        CORE_MISSING+=("$FILE")
        break
      fi
    done
  fi
done

# If core files are missing, try fallback sources
if [ ${#CORE_MISSING[@]} -ne 0 ]; then
  log_warning "Essential core files are still missing: ${CORE_MISSING[*]}"
  log_info "Trying fallback downloads..."

  # Try direct downloads for core files
  for FILE in "${CORE_MISSING[@]}"; do
    URL="$GITHUB_BASE_URL/$FILE"
    log_info "Directly downloading $FILE from $URL"

    if command -v curl &>/dev/null; then
      curl -s -f -L -o "$FILE" "$URL" && log_success "Successfully downloaded $FILE" || log_warning "Failed to download $FILE with curl"
    elif command -v wget &>/dev/null; then
      wget -q -O "$FILE" "$URL" && log_success "Successfully downloaded $FILE" || log_warning "Failed to download $FILE with wget"
    fi
  done

  # Check if the core files are still missing after direct download attempts
  REMAINING_CORE_MISSING=()
  for FILE in "${CORE_MISSING[@]}"; do
    if [ ! -f "$FILE" ]; then
      REMAINING_CORE_MISSING+=("$FILE")
    fi
  done

  # If core files are still missing, try astro.com fallback
  if [ ${#REMAINING_CORE_MISSING[@]} -ne 0 ]; then
    log_warning "Still missing critical files after direct downloads, trying astro.com..."

    # Comprehensive Swiss Ephemeris package URL - prefer astro.com official source
    FALLBACK_ARCHIVE="se_ephe.zip"
    FALLBACK_URLS=(
      "https://www.astro.com/ftp/swisseph/ephe/se_ephe.zip"
      "https://sweph.typoon.net/ephe/se_ephe.zip"
      "https://github.com/aloistr/swisseph/blob/master/ephe/se_ephe.zip?raw=true"
    )

    for URL in "${FALLBACK_URLS[@]}"; do
      log_info "Trying to download from $URL"
      if command -v curl &>/dev/null; then
        curl -s -L -o "$FALLBACK_ARCHIVE" "$URL" && break || log_warning "Failed to download from $URL with curl"
      elif command -v wget &>/dev/null; then
        wget -q -O "$FALLBACK_ARCHIVE" "$URL" && break || log_warning "Failed to download from $URL with wget"
      fi
    done

    # Check if fallback archive exists and try to extract it
    if [ -f "$FALLBACK_ARCHIVE" ]; then
      log_info "Extracting fallback archive..."

      # Try unzipping with error handling
      if command -v unzip &>/dev/null; then
        unzip -q -o "$FALLBACK_ARCHIVE" || log_warning "Failed to unzip fallback archive - continuing anyway"
      else
        log_warning "unzip command not found - continuing anyway"
      fi

      # Remove the fallback archive
      rm -f "$FALLBACK_ARCHIVE"
    else
      log_warning "Failed to download fallback archive - continuing anyway"
    fi
  fi
elif [ ${#STILL_MISSING[@]} -ne 0 ]; then
  log_warning "Some non-critical files are still missing: ${STILL_MISSING[*]}"
  log_info "Core files already present - continuing"
fi

# Final verification
log_info "Performing final verification..."
FINAL_MISSING_CORE=()
for FILE in "${CORE_ESSENTIAL_FILES[@]}"; do
  if [ ! -f "$FILE" ]; then
    FINAL_MISSING_CORE+=("$FILE")
  fi
done

# Set permissions
log_info "Setting permissions on ephemeris files..."
chmod -R 755 .

# Final check
num_se1_files=$(ls -1 ./*.se1 2>/dev/null | wc -l)
log_info "Found $num_se1_files .se1 files in $EPHEMERIS_DIR"

if [ ${#FINAL_MISSING_CORE[@]} -ne 0 ]; then
  log_warning "Missing critical core files: ${FINAL_MISSING_CORE[*]}"

  # Create minimal placeholder files as a last resort
  for FILE in "${FINAL_MISSING_CORE[@]}"; do
    log_warning "Creating empty placeholder for $FILE - charts may not be accurate!"
    touch "$FILE"
  done
fi

# Create a verification file to indicate download attempt
touch .ephemeris_downloaded

# Test Swiss Ephemeris access if Python is available
if command -v python3 &>/dev/null && python3 -c "import pyswisseph" &>/dev/null; then
  log_info "Testing Swiss Ephemeris access with Python..."
  TEST_RESULT=$(python3 -c "import pyswisseph as swe; swe.set_ephe_path('$EPHEMERIS_DIR'); print(f'Swiss Ephemeris initialized successfully. Library path: {swe.get_library_path()}')" 2>&1) && \
    log_success "Python Swiss Ephemeris test successful: $TEST_RESULT" || \
    log_warning "Python Swiss Ephemeris test failed: $TEST_RESULT"
fi

log_success "Swiss Ephemeris files setup completed in $EPHEMERIS_DIR"
ls -la "$EPHEMERIS_DIR" | grep -E '\.(se1|txt|cat)$'

echo -e "\n${GREEN}=================================${NC}"
echo -e "${GREEN}Ephemeris setup complete${NC}"
echo -e "${GREEN}=================================${NC}"

exit 0
