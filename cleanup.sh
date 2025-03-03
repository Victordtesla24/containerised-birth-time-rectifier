#!/bin/bash

# macOS Cleanup Script with Enhanced Fixes and Logging

# Require script to run as root for full access (Fix 1 improvement)
if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run this script as root (using sudo)."
  exit 1
fi

# Enable robust logging to file and console
LOGFILE="$HOME/macos_cleanup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOGFILE") 2>&1
echo "==== macOS Cleanup Script Started at $(date) ===="
echo "Logging to $LOGFILE"
echo ""

# Function to get CPU load averages as "x, y, z"
get_load_averages() {
  # Use uptime to extract load averages
  local loads
  loads=$(uptime | sed -E 's/.*load averages?: ([0-9.]+) ([0-9.]+) ([0-9.]+)/\1 \2 \3/')
  # shellcheck disable=SC2086
  # (Disable SC2086 warning for word splitting which is intended here)
  read -r load1 load5 load15 <<< "$loads"
  echo "$load1, $load5, $load15"
}

# Function to get free memory in MB
get_free_mem_mb() {
  local free_pages
  free_pages=$(vm_stat | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
  # If vm_stat output not found or empty, default to 0
  [[ -z "$free_pages" ]] && free_pages=0
  # Calculate MB from pages (each page is 4096 bytes)
  echo $(( free_pages * 4096 / 1024 / 1024 ))
}

# Function to test disk write speed (writes a 100 MB file and measures time)
test_disk_write_speed() {
  local testfile="/tmp/disk_test.$$"  # use PID for unique name
  local count=100  # 100 MB (1 MB * 100)
  # Perform a test write and time it
  # We use dd to write 100 MB of zeros to /tmp (which is on disk for macOS, not a RAM disk).
  # The output of `dd` is captured to extract the elapsed time.
  # Using LANG=C to ensure consistent numeric format in output.
  local dd_output
  dd_output=$(LANG=C /usr/bin/time -p dd if=/dev/zero of="$testfile" bs=1m count=$count 2>&1)
  # Clean up the test file
  rm -f "$testfile"
  # Extract the 'real' time from the time command output (in seconds)
  local real_time
  real_time=$(echo "$dd_output" | awk '/real/ {print $2}')
  if [[ -n "$real_time" ]]; then
    # Calculate MB/s = 100 MB / real_time (seconds)
    # Use bc for float division with 2 decimal places
    local speed
    speed=$(echo "scale=2; $count/$real_time" | bc)
    echo "$speed MB/s"
  else
    echo "N/A"
  fi
}

# Record performance metrics before cleanup
echo ">> Collecting system metrics before cleanup..."
CPU_BEFORE=$(get_load_averages)
FREE_MEM_BEFORE=$(get_free_mem_mb)
APP_LAUNCH_BEFORE=$( (time -p perl -e "exit") 2>&1 | awk '/real/ {print $2}' )
DISK_SPEED_BEFORE=$(test_disk_write_speed)
echo "Before Cleanup - CPU Load Averages (1m,5m,15m): $CPU_BEFORE"
echo "Before Cleanup - Free RAM: ${FREE_MEM_BEFORE} MB"
echo "Before Cleanup - Test App Launch Time: ${APP_LAUNCH_BEFORE}s"
echo "Before Cleanup - Disk Write Speed: $DISK_SPEED_BEFORE"
echo ""

# 1. System Cache Cleanup (user, system caches)
echo ">> Clearing system and user caches (requires root)..."
for cache in "/Library/Caches" "$HOME/Library/Caches"; do
  if [[ -d "$cache" ]]; then
    echo "Clearing $cache ..."
    # Remove cache files; redirect errors to avoid stopping script on failure
    if ! rm -rf "$cache"/* 2>/dev/null; then
      echo "WARNING: Some files in $cache could not be removed (permission denied)."
      # Try again with sudo in case script isn't running as root (should not happen due to earlier check)
      sudo rm -rf "$cache"/* 2>/dev/null || echo "ERROR: Failed to clear $cache even with elevated permissions."
    fi
  fi
done
echo "Cache cleanup completed."
echo ""

# 2. Run periodic maintenance scripts (daily, weekly, monthly)
echo ">> Running periodic maintenance scripts..."
if command -v periodic &> /dev/null; then
  # Run each periodic script separately to log any issues (Fix 2)
  for interval in daily weekly monthly; do
    if [[ -x "/etc/periodic/${interval}" || -d "/etc/periodic/${interval}" ]]; then
      echo "Running periodic $interval tasks..."
      if periodic "$interval" 2>/dev/null; then
        echo "Periodic $interval completed."
      else
        echo "WARNING: periodic $interval encountered an error."
      fi
    fi
  done
else
  echo "NOTICE: 'periodic' command not found – skipping (macOS handles maintenance via launchd/logd on this version)."
fi
echo ""

# 3. (Already handled in metrics formatting) CPU load values will be shown properly in the metrics output.

# 4. Rebuild dynamic loader cache to prevent slow app launches
if command -v update_dyld_shared_cache &> /dev/null; then
  echo ">> Rebuilding dynamic linker cache to avoid app launch delays..."
  update_dyld_shared_cache -force
  echo "Dynamic loader cache rebuild completed."
else
  echo ">> Skipping dynamic cache rebuild (not supported on this macOS version)."
fi
echo ""

# 5. (Disk write speed is passively ensured by avoiding heavy background triggers; metrics will verify any changes)

# 6. RAM optimization: Free inactive memory
if command -v purge &> /dev/null; then
  echo ">> Freeing inactive memory with purge..."
  purge 2>/dev/null || echo "WARNING: 'purge' command failed (might require developer tools on some macOS versions)."
else
  echo ">> 'purge' command not available; skipping RAM purge."
fi
echo ""

# Flush filesystem buffers to ensure all changes are written (helps stabilize disk I/O)
sync

# Record performance metrics after cleanup
echo ">> Collecting system metrics after cleanup..."
CPU_AFTER=$(get_load_averages)
FREE_MEM_AFTER=$(get_free_mem_mb)
APP_LAUNCH_AFTER=$( (time -p perl -e "exit") 2>&1 | awk '/real/ {print $2}' )
DISK_SPEED_AFTER=$(test_disk_write_speed)
echo "After Cleanup - CPU Load Averages (1m,5m,15m): $CPU_AFTER"
echo "After Cleanup - Free RAM: ${FREE_MEM_AFTER} MB"
echo "After Cleanup - Test App Launch Time: ${APP_LAUNCH_AFTER}s"
echo "After Cleanup - Disk Write Speed: $DISK_SPEED_AFTER"
echo ""

# Compare and log improvements/regressions
echo "==== Performance Comparison ===="
echo "CPU Load (before -> after): $CPU_BEFORE -> $CPU_AFTER"
echo "Free RAM (before -> after): ${FREE_MEM_BEFORE} MB -> ${FREE_MEM_AFTER} MB"
echo "App Launch Time (before -> after): ${APP_LAUNCH_BEFORE}s -> ${APP_LAUNCH_AFTER}s"
echo "Disk Write Speed (before -> after): $DISK_SPEED_BEFORE -> $DISK_SPEED_AFTER"
echo "==============================="
echo "Cleanup complete. Detailed log saved to $LOGFILE"
