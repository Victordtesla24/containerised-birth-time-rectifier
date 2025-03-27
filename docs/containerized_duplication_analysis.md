# Containerized Duplication Detection

The code duplication detection tool provides a comprehensive analysis of your codebase to identify similar code patterns, hardcoded values, mocked implementations, fallback mechanisms, and error masking. The tool is now containerized to allow for more efficient and resource-friendly execution, freeing up your local machine for other tasks.

## Key Features

- **GPU Acceleration**: Leverages NVIDIA CUDA for faster analysis of large codebases when available
- **Interactive HTML Reports**: Generates detailed reports with interactive visualizations
- **Network Analysis**: Shows the relationships between duplicated files with force-directed graphs
- **Multiple Detection Methods**: Combines token-based, AST-based, and control flow analysis
- **Resource Isolation**: Runs in a container to avoid impacting your local development environment

## Requirements

- Docker
- NVIDIA GPU with CUDA support (optional, for acceleration)
- Docker Compose (optional, for simplified deployment)

## Getting Started

The tool can be run in two modes:

1. **Direct Docker Mode**: Simple execution with docker commands
2. **Docker Compose Mode**: More configurable setup using docker-compose

### Running the Analysis

The easiest way to run the analysis is to use the provided script:

```bash
./run_duplication_analysis.sh [options] [directory1] [directory2] ...
```

#### Options

- `-h, --help`: Show help message
- `-s, --server`: Run in server mode to keep the container running and serve HTML reports
- `--no-gpu`: Disable GPU support
- `-q, --quick`: Run quick analysis (faster but less accurate)
- `-v, --verbose`: Enable verbose output
- `-c, --compose`: Use docker-compose instead of direct docker run

#### Examples

```bash
# Analyze both AI Service and API Gateway
./run_duplication_analysis.sh ai_service api_gateway

# Quick analysis of just the AI service
./run_duplication_analysis.sh -q ai_service

# Start in server mode to browse reports
./run_duplication_analysis.sh -s

# Use docker-compose in server mode
./run_duplication_analysis.sh -c -s
```

## Report Visualization

After the analysis completes, an HTML report is generated in the `reports/duplication` directory. This report includes:

- Summary statistics of analyzed files
- Charts showing types of duplications found
- Network visualization of file relationships
- Detailed lists of similar files
- Code patterns that repeat across the codebase

In server mode, you can access the report through a web browser at:
```
http://localhost:8050
```

## Advanced Configuration

For more advanced configurations, you can edit the `docker-compose.duplication.yml` file. Key settings include:

- Container resources (memory, CPU limits)
- GPU allocation
- Network configuration
- Volume mounts

## How It Works

The containerized analyzer works in three phases:

1. **Rapid Hashing Layer**: Quick identification of exact duplicates
2. **AST Pattern Matching**: Deep analysis of code structure
3. **Control Flow Analysis**: Detection of semantically similar code

These phases are accelerated using GPU computing when available, with the TensorFlow and PyTorch libraries handling the computational load.

## Integration with CI/CD

You can integrate this tool into your CI/CD pipeline by adding steps to your workflow:

```yaml
# Example GitHub Actions workflow
duplication-analysis:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Run Duplication Analysis
      run: |
        docker pull ghcr.io/your-org/code-duplication-analyzer:latest
        docker run --rm \
          -v ${GITHUB_WORKSPACE}:/code \
          -v ${GITHUB_WORKSPACE}/reports:/mounted_reports \
          ghcr.io/your-org/code-duplication-analyzer:latest
    - name: Upload Reports
      uses: actions/upload-artifact@v2
      with:
        name: duplication-reports
        path: reports/duplication
```

## Troubleshooting

### GPU Issues

If the analysis is not using the GPU:

1. Verify GPU is detected: `nvidia-smi`
2. Ensure Docker has GPU access: `docker run --gpus all nvidia/cuda:11.0-base nvidia-smi`
3. Try running with the `--no-gpu` flag to force CPU mode

### Container Build Errors

If the container fails to build:

1. Check Docker logs: `docker logs [container_id]`
2. Verify your Docker version: `docker --version`
3. Free up disk space if needed

### Report Generation Failures

If reports are not generating correctly:

1. Check permissions on the reports directory
2. Run in verbose mode for more details: `-v`
3. Check for errors in the container logs
