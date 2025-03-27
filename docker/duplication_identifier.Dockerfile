FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

LABEL maintainer="AI-Assisted Development Team"
LABEL description="Code Duplication Identifier with GPU Acceleration"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    jq \
    curl \
    ca-certificates \
    tree \
    git \
    xz-utils \
    libffi-dev \
    libssl-dev \
    bc \
    ripgrep \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies for analysis
RUN pip install --upgrade pip setuptools wheel && \
    pip install numpy pandas matplotlib seaborn jinja2 markupsafe torch jupyterlab \
    networkx scikit-learn tensorflow scikit-learn-intelex pytest flask markdown && \
    pip install plotly dash dash-bootstrap-components dash-daq && \
    pip install onnxruntime-gpu

# Copy duplication detection scripts
COPY tests/shell_scripts/duplication_identifier.sh /app/duplication_identifier.sh
COPY tests/shell_scripts/cleanup/modules /app/modules

# Create report directory
RUN mkdir -p /app/reports

# Set script permissions
RUN chmod +x /app/duplication_identifier.sh
RUN chmod +x /app/modules/*.sh

# Create HTML visualizer script
COPY docker/scripts/visualize_report.py /app/visualize_report.py

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "===== Code Duplication Identifier with GPU Acceleration ====="\n\
# Check GPU availability\n\
if [ -x "$(command -v nvidia-smi)" ]; then\n\
  echo "GPU detected:"\n\
  nvidia-smi\n\
  export HAS_GPU=true\n\
else\n\
  echo "No GPU detected, using CPU only."\n\
  export HAS_GPU=false\n\
fi\n\
\n\
# Create directories if they don\'t exist\n\
mkdir -p /app/reports\n\
\n\
# Run the duplication identifier with the provided arguments\n\
echo "Running duplication analysis..."\n\
cd /app\n\
if [ $# -gt 0 ]; then\n\
  ./duplication_identifier.sh "$@"\n\
  exit_code=$?\n\
else\n\
  echo "No arguments provided. Using default directories."\n\
  ./duplication_identifier.sh -v /code\n\
  exit_code=$?\n\
fi\n\
\n\
# Generate HTML report\n\
if [ $exit_code -eq 0 ]; then\n\
  echo "Analysis completed. Generating HTML report..."\n\
  latest_report=$(find /app/reports -type d -name "duplication_*" | sort -r | head -n 1)\n\
  if [ -n "$latest_report" ]; then\n\
    # Run the visualization script\n\
    python /app/visualize_report.py "$latest_report"\n\
    \n\
    # Copy reports to mounted volume\n\
    if [ -d "/mounted_reports" ]; then\n\
      cp -r "$latest_report"/* /mounted_reports/\n\
      echo "Reports available in mounted directory: /mounted_reports"\n\
    else\n\
      echo "Reports available in: $latest_report"\n\
    fi\n\
  else\n\
    echo "No reports generated."\n\
  fi\n\
fi\n\
\n\
# Keep container running if in server mode\n\
if [ "$SERVER_MODE" = "true" ]; then\n\
  echo "Server mode enabled. Starting visualization server..."\n\
  python -m flask run --host=0.0.0.0 --port=8050\n\
else\n\
  exit $exit_code\n\
fi\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose port for visualization server
EXPOSE 8050

# Set environment variables
ENV PYTHONPATH="/app"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
