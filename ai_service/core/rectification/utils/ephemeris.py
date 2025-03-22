"""
Ephemeris file management for astrological calculations.
"""
import os
import logging
import urllib.request
import zipfile
from pathlib import Path
import shutil
import tempfile

logger = logging.getLogger(__name__)

def verify_ephemeris_files():
    """
    Verify that ephemeris files exist and download them if missing.

    Returns:
        bool: True if files are now available, False if verification failed
    """
    # Define path to ephemeris directory
    ephemeris_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ephemeris")

    # Create directory if it doesn't exist
    if not os.path.exists(ephemeris_path):
        os.makedirs(ephemeris_path, exist_ok=True)
        logger.info(f"Created ephemeris directory at {ephemeris_path}")

    # Check if directory is empty or missing essential files
    essential_files = ["sepl_18.se1", "semo_18.se1", "seas_18.se1", "seasnam.txt"]
    missing_files = [f for f in essential_files if not os.path.exists(os.path.join(ephemeris_path, f))]

    if missing_files:
        logger.warning(f"Missing essential ephemeris files: {missing_files}. Attempting to download...")

        try:
            # GitHub repository URLs for direct file downloads
            github_base_url = "https://raw.githubusercontent.com/astro-pro/ephe/master/"

            # Download each file individually
            for file_name in missing_files:
                # Use proper URL format for GitHub raw files
                if file_name == "sepl_18.se1":
                    file_url = f"{github_base_url}sepl_18.se1"
                elif file_name == "semo_18.se1":
                    file_url = f"{github_base_url}semo_18.se1"
                elif file_name == "seas_18.se1":
                    file_url = f"{github_base_url}seas_18.se1"
                elif file_name == "seasnam.txt":
                    file_url = f"{github_base_url}seasnam.txt"
                else:
                    continue

                logger.info(f"Downloading {file_name} from {file_url}")

                # Safe download with temp file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    try:
                        urllib.request.urlretrieve(file_url, temp_file.name)
                        # Copy to final destination if download successful
                        shutil.copy2(temp_file.name, os.path.join(ephemeris_path, file_name))
                        logger.info(f"Successfully downloaded {file_name}")
                    except Exception as e:
                        logger.error(f"Error downloading {file_name}: {e}")
                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_file.name):
                            os.unlink(temp_file.name)

            # Verify files were downloaded successfully
            still_missing = [f for f in essential_files if not os.path.exists(os.path.join(ephemeris_path, f))]
            if still_missing:
                logger.error(f"Failed to download all required ephemeris files. Still missing: {still_missing}")
                return False

            logger.info("Successfully downloaded ephemeris files")
            return True

        except Exception as e:
            logger.error(f"Error downloading ephemeris files: {e}")
            return False

    logger.info("Ephemeris files verified and available")
    return True
