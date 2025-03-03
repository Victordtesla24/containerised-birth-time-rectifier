# Birth Time Rectifier Scripts

This directory contains utility scripts for managing the Birth Time Rectifier application.

## Management Scripts

The following unified management scripts are available:

### Directory Management

```bash
./manage-directories.sh [OPTION]
```

Options:
- `--cleanup`: Clean up temporary files only (safe)
- `--consolidate`: Run directory consolidation (use with caution!)
- `--finalize`: Finalize consolidation (use with caution!)
- `--help`: Show help message

### Container Management

```bash
./manage-containers.sh [OPTION]
```

Options:
- `--run [dev|prod]`: Build and run containers (dev mode by default)
- `--test [dev|prod]`: Test containers (dev mode by default)
- `--stop`: Stop running containers
- `--clean`: Stop and remove containers, volumes, and images
- `--help`: Show help message

## Individual Scripts

These scripts are used by the management scripts above, but can also be run individually:

### Directory Management

- `cleanup-temp-files.js`: Cleans up temporary files
- `consolidate-directories.js`: Consolidates duplicate directories
- `cleanup-consolidation.js`: Finalizes directory consolidation

### Container Management

- `run_containers.sh`: Builds and runs containers
- `test_containers.sh`: Tests containers
- `verify_gpu.py`: Verifies GPU availability

## Development Scripts

- `setup-images.js`: Sets up image assets

## Usage Examples

### Clean up temporary files

```bash
./manage-directories.sh --cleanup
```

### Run containers in development mode

```bash
./manage-containers.sh --run dev
```

### Test containers in production mode

```bash
./manage-containers.sh --test prod
```

### Stop containers

```bash
./manage-containers.sh --stop
```

## Integration with Test Suite

The `run_all_tests.sh` script in the `tests` directory can use these scripts with the following options:

```bash
# Run tests including Docker container tests
../tests/run_all_tests.sh --docker

# Run tests with Docker in production mode
../tests/run_all_tests.sh --docker --docker-mode prod

# Run tests and cleanup temporary files after
../tests/run_all_tests.sh --cleanup

# Detect and analyze duplicate files across the codebase
../tests/run_all_tests.sh --remove-duplicates
```

### Duplicate File Management

The `run_all_tests.sh` script now includes functionality for detecting and removing duplicate files according to the directory management protocols. This integration leverages the `manage-directories.sh` script for safe consolidation of duplicates:

1. **Detect Duplicates Only**:
   ```bash
   ../tests/run_all_tests.sh --remove-duplicates
   ```
   This will scan the codebase for duplicate files and create a detailed report in the test results directory without making any changes.

2. **Report Contents**:
   - Exact duplicate files (identical content in different locations)
   - JavaScript/TypeScript modules with similar exports
   - Python modules with similar functions
   - Shell scripts with similar functionality

3. **Process**:
   - Creates backups of all files before any changes
   - Uses `manage-directories.sh --consolidate` to safely merge duplicates
   - Runs verification tests after consolidation
   - Generates a detailed report of all actions

4. **Best Practices**:
   - Always review the report before authorizing changes
   - Run verification tests after consolidation
   - Keep backups until you've verified everything works
   - For major restructuring, consider finalizing in stages

## Available Scripts

### Directory Management

- **`consolidate-directories.js`**: Consolidates duplicate directories and files to streamline the project structure.
  - Merges files from multiple directories into a single target directory
  - Creates backups of all modified files
  - Runs a lint check to verify integrity

- **`cleanup-consolidation.js`**: Finalizes the consolidation process by safely removing consolidated directories.
  - Checks if any files remain in source directories
  - Provides a summary of what will be removed
  - Creates backups before removing anything
  - Provides rollback instructions in case of issues

### Maintenance

- **`cleanup-temp-files.js`**: Periodically cleans up temporary files and maintains a clean directory structure.
  - Removes build artifacts and temporary files (like .DS_Store, .pyc files)
  - Cleans up cache directories like __pycache__ and .pytest_cache
  - Rotates log files older than 7 days
  - Automatically creates timestamps for rotated logs

## Usage

### Directory Consolidation Process

1. **Step 1: Run Consolidation**
   ```bash
   node scripts/consolidate-directories.js
   ```
   This will merge files from source directories into target directories based on the configuration in the script.

2. **Step 2: Verify Consolidation**
   - Check that the application functions correctly after consolidation
   - Review any linting errors and fix them
   - Make sure all features are working as expected

3. **Step 3: Clean Up**
   ```bash
   node scripts/cleanup-consolidation.js
   ```
   This will check for any remaining files in the source directories and allow you to safely remove them.

### Maintenance Tasks

1. **Cleaning Temporary Files**
   ```bash
   node scripts/cleanup-temp-files.js
   ```
   Run this periodically to remove temporary files, caches, and rotate old logs.
   Consider scheduling this as a cron job for regular maintenance.

## Best Practices

- **Always verify** that the application functions correctly after running any scripts
- **Check the backups** created in `.backups/consolidation` and `.backups/rollback_consolidation` before making any changes
- **Never skip the verification step** between consolidation and cleanup
- **Run maintenance scripts regularly** to keep the project directory clean and optimized

## Adding New Scripts

When adding new scripts to this directory:

1. Make sure to document the script in this README
2. Add proper error handling and logging
3. Always create backups before destructive operations
4. Make scripts executable with `chmod +x script-name.js`

## Lessons Learned From Consolidation

### Directory Structure
- Keep related files together in logical directories (`/src` for frontend, `/ai_service` for AI)
- Avoid duplicating code across multiple locations
- Maintain a clear separation of concerns between services

### Code Quality
- Consistent code style across the entire codebase is essential
- Prefer type-safe implementations over any types
- Use proper logging instead of console statements
- Keep dependencies updated and consistent across the project

### Process Improvements
- Always create backups before major restructuring
- Test thoroughly after any significant changes
- Document changes and decisions for future reference
- Use automation scripts for repetitive tasks
- Run linting checks after changes to ensure quality

### Future Considerations
- Consider implementing a monorepo structure for better management of multi-service applications
- Explore using workspaces for package management
- Implement stricter linting rules to prevent quality regression
- Add automated tests for critical paths to detect issues early
