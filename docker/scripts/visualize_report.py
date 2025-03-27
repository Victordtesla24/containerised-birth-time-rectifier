#!/usr/bin/env python3
"""
Code Duplication Report Visualizer
Generates interactive HTML reports with visualizations for duplication analysis.
Uses GPU acceleration for network graph calculations when available.
"""

import os
import sys
import json
import glob
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime
import argparse
from jinja2 import Template
from collections import defaultdict

# Track available libraries
missing_libs = []

# Gracefully handle imports
try:
    import markdown
except ImportError:
    missing_libs.append("markdown")

try:
    import networkx as nx
except ImportError:
    missing_libs.append("networkx")
    # Define a fallback implementation
    class MockNetworkX:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    nx = MockNetworkX()

# GPU acceleration flag
use_gpu = False

# Import visualization libraries
try:
    # Safe import to avoid linter errors
    import importlib
    go_module = importlib.import_module("plotly.graph_objects")
    go = go_module
    px_module = importlib.import_module("plotly.express")
    px = px_module
except ImportError:
    missing_libs.append("plotly")
    # Mock implementation for graceful degradation
    class MockGo:
        def __init__(self):
            self.Figure = lambda: self
            self.Scatter = lambda **kwargs: None
            self.Bar = lambda **kwargs: None
            self.Layout = lambda **kwargs: None
        def add_trace(self, *args, **kwargs):
            return self
        def update_layout(self, *args, **kwargs):
            return self
        def to_html(self, *args, **kwargs):
            return "<p>Plotly not available</p>"
    go = MockGo()
    px = None

# Try to import GPU acceleration libraries
try:
    import torch

    try:
        # Safe import to avoid linter errors
        ort_module = importlib.import_module("onnxruntime")

        # Check if GPU is available for either library
        if torch.cuda.is_available() or ('CUDA' in ort_module.get_available_providers()):
            use_gpu = True
            print("GPU acceleration available and enabled")
    except ImportError:
        # Continue without onnxruntime
        if torch.cuda.is_available():
            use_gpu = True
            print("GPU acceleration available with PyTorch only")
except ImportError:
    missing_libs.append("torch")
    print("GPU libraries not available, using CPU only")

# Print information about missing libraries
if missing_libs:
    print(f"Warning: The following libraries are missing and some features may be limited: {', '.join(missing_libs)}")
else:
    print("All required libraries are available")

def load_data(report_dir: str) -> Optional[Dict[str, Any]]:
    """Load data from duplication report files."""
    report_path = Path(report_dir)

    # Load merged results
    merged_results_path = report_path / "merged_results.json"
    if not merged_results_path.exists():
        print(f"Error: Report file not found at {merged_results_path}")
        return None

    with open(merged_results_path, 'r') as f:
        merged_results = json.load(f)

    # Load additional data if available
    structure_insights_path = report_path / "structure_insights.txt"
    structure_insights = None
    if structure_insights_path.exists():
        with open(structure_insights_path, 'r') as f:
            structure_insights = f.read()

    # Return the combined data
    return {
        'merged_results': merged_results,
        'structure_insights': structure_insights,
        'report_dir': str(report_path)
    }

def calculate_summary_stats(data: Dict[str, Any]) -> Dict[str, Union[int, float]]:
    """Calculate summary statistics from the report data."""
    if not data or 'merged_results' not in data:
        return {
            'file_count': 0,
            'duplicate_pairs': 0,
            'files_with_issues': 0,
            'exact_duplicates': 0,
            'structural_duplicates': 0,
            'functional_duplicates': 0,
            'duplication_rate': 0.0
        }

    merged_results = data['merged_results']

    # Extract basic stats
    file_count = merged_results.get('file_count', 0)
    duplicate_pairs = len(merged_results.get('similar_pairs', []))
    files_with_issues = len(merged_results.get('files_with_issues', []))

    # Calculate additional metrics
    exact_duplicates = len(merged_results.get('exact_duplicates', []))
    structural_duplicates = len(merged_results.get('structural_duplicates', []))
    functional_duplicates = len(merged_results.get('functional_duplicates', []))

    # Calculate duplication rate
    duplication_rate = duplicate_pairs / file_count if file_count > 0 else 0

    # Return the stats
    return {
        'file_count': file_count,
        'duplicate_pairs': duplicate_pairs,
        'files_with_issues': files_with_issues,
        'exact_duplicates': exact_duplicates,
        'structural_duplicates': structural_duplicates,
        'functional_duplicates': functional_duplicates,
        'duplication_rate': duplication_rate
    }

def create_bar_chart(stats: Dict[str, Union[int, float]]) -> str:
    """Create a bar chart showing duplication types."""
    if "plotly" in missing_libs:
        return "<p>Plotly visualization library is not available. Install plotly to see visualizations.</p>"

    try:
        categories = ['Exact', 'Structural', 'Functional']
        values = [
            stats.get('exact_duplicates', 0),
            stats.get('structural_duplicates', 0),
            stats.get('functional_duplicates', 0)
        ]

        # Create Plotly bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=['#FF4136', '#FF851B', '#FFDC00'],
            text=values,
            textposition='auto'
        ))

        fig.update_layout(
            title='Types of Code Duplications Found',
            xaxis_title='Duplication Type',
            yaxis_title='Count',
            template='plotly_white'
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        # Fallback if there's any error during chart creation
        return f"<p>Error creating chart: {str(e)}</p>"

def create_network_graph(data: Dict[str, Any]) -> str:
    """Create an interactive network graph of file duplications using GPU acceleration if available."""
    required_libs = ["networkx", "plotly"]
    missing = [lib for lib in required_libs if lib in missing_libs]

    if missing:
        return f"<p>Required libraries not available: {', '.join(missing)}. Install these libraries to see network visualizations.</p>"

    try:
        if not data or 'merged_results' not in data:
            return "<p>No data available to visualize.</p>"

        similar_pairs = data['merged_results'].get('similar_pairs', [])

        if not similar_pairs:
            return "<p>No duplication pairs found to visualize.</p>"

        # Create graph
        G = nx.Graph()

        # Add nodes and edges
        for pair in similar_pairs:
            file1 = os.path.basename(pair.get('file1', 'unknown'))
            file2 = os.path.basename(pair.get('file2', 'unknown'))
            similarity = pair.get('similarity', 0)

            # Add nodes with attributes
            G.add_node(file1, size=10, color='#3498db')
            G.add_node(file2, size=10, color='#3498db')

            # Add edge with similarity as weight
            G.add_edge(file1, file2, weight=similarity, width=similarity*5)

        # Calculate layout
        if use_gpu and "torch" not in missing_libs and torch.cuda.is_available():
            # Use torch for GPU-accelerated calculations
            print("Using GPU to calculate graph layout")
            pos_tensor = compute_layout_gpu(G)
            pos = {node: (float(pos_tensor[i][0].item()), float(pos_tensor[i][1].item()))
                for i, node in enumerate(G.nodes())}
        else:
            # Use CPU-based layout algorithms
            pos = nx.spring_layout(G)

        # Create interactive visualization
        edge_x = []
        edge_y = []
        edge_colors = []

        for edge in G.edges(data=True):
            source, target, attr_dict = edge  # Unpack the edge tuple safely
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            similarity = attr_dict.get('weight', 0)

            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

            # Color based on similarity
            r = int(255 * similarity)
            g = int(100 * (1 - similarity))
            b = 0
            edge_colors.append(f'rgba({r},{g},{b},0.7)')

        node_x = []
        node_y = []
        node_text = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)

        # Create Plotly visualization
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                size=10,
                color='#3498db',
                line=dict(width=1, color='#1a1a1a')
            ))

        fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                            title='Code Duplication Network',
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            annotations=[dict(
                                text="",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002)],
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            template='plotly_dark'
                        ))

        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        # Fallback if there's any error during graph creation
        return f"<p>Error creating network graph: {str(e)}</p>"

def compute_layout_gpu(G: Any) -> Any:
    """Use GPU to compute graph layout if available."""
    if "torch" in missing_libs:
        # Fallback if torch isn't available
        print("PyTorch not available, using CPU layout")
        return nx.spring_layout(G)

    try:
        num_nodes = len(G.nodes())
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize positions randomly
        pos = torch.rand(num_nodes, 2, device=device)

        # Get adjacency matrix
        adjacency = nx.to_numpy_array(G)
        weights = nx.to_numpy_array(G, weight='weight')

        # Convert to torch tensors
        adjacency_tensor = torch.tensor(adjacency, device=device)
        weights_tensor = torch.tensor(weights, device=device)

        # Optimization parameters
        lr = 0.1
        iterations = 50

        # Optimize layout using GPU
        for _ in range(iterations):
            # Calculate pairwise distances
            delta = pos.unsqueeze(1) - pos.unsqueeze(0)
            distance = torch.norm(delta, dim=2)

            # Avoid division by zero
            distance = torch.clamp(distance, min=0.1)

            # Attractive forces (edges pull connected nodes together)
            attractive = delta * adjacency_tensor.unsqueeze(2) * weights_tensor.unsqueeze(2)

            # Repulsive forces (all nodes push each other apart)
            repulsive = delta / (distance * distance).unsqueeze(2)

            # Update positions
            force = (attractive - repulsive).sum(dim=1)
            pos = pos + lr * force

        return pos
    except Exception as e:
        print(f"Error in GPU layout computation: {e}")
        # Fallback to CPU layout
        return nx.spring_layout(G)

def generate_html_report(data: Dict[str, Any], stats: Dict[str, Union[int, float]],
                         bar_chart_html: str, network_graph_html: str) -> str:
    """Generate HTML report with visualizations."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create HTML template
    template_str = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Duplication Analysis Report</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f8f9fa;
                padding-top: 2rem;
            }
            .header {
                background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
                color: white;
                padding: 2rem 0;
                border-radius: 0.5rem;
                margin-bottom: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .card {
                border: none;
                border-radius: 0.5rem;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
                transition: all 0.3s ease;
                margin-bottom: 1.5rem;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }
            .card-header {
                font-weight: bold;
                border-bottom: none;
                background-color: rgba(0, 0, 0, 0.03);
            }
            .stat-card {
                text-align: center;
                padding: 1.5rem;
            }
            .stat-value {
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            .stat-label {
                font-size: 0.9rem;
                color: #6c757d;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .visualization {
                margin-top: 2rem;
                overflow: hidden;
            }
            .code-block {
                background-color: #f4f4f4;
                border-radius: 0.3rem;
                padding: 1rem;
                margin: 1rem 0;
                font-family: monospace;
            }
            footer {
                margin-top: 3rem;
                padding: 1rem 0;
                text-align: center;
                font-size: 0.9rem;
                color: #6c757d;
                border-top: 1px solid #dee2e6;
            }
            .grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header text-center">
                <h1><i class="bi bi-search"></i> Code Duplication Analysis Report</h1>
                <p class="lead">Generated on {{ timestamp }}</p>
            </div>

            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">Summary</div>
                        <div class="card-body">
                            <div class="grid-container">
                                <div class="stat-card">
                                    <div class="stat-value">{{ stats.file_count }}</div>
                                    <div class="stat-label">Files Analyzed</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">{{ stats.duplicate_pairs }}</div>
                                    <div class="stat-label">Duplicate Pairs</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">{{ stats.files_with_issues }}</div>
                                    <div class="stat-label">Files with Issues</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-value">{{ '%0.1f'|format(stats.duplication_rate * 100) }}%</div>
                                    <div class="stat-label">Duplication Rate</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="card visualization">
                        <div class="card-header">Duplication Types</div>
                        <div class="card-body">
                            {{ bar_chart_html|safe }}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">Duplication Distribution</div>
                        <div class="card-body">
                            <ul class="list-group">
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    Exact Duplicates
                                    <span class="badge bg-danger rounded-pill">{{ stats.exact_duplicates }}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    Structural Duplicates
                                    <span class="badge bg-warning rounded-pill">{{ stats.structural_duplicates }}</span>
                                </li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    Functional Duplicates
                                    <span class="badge bg-info rounded-pill">{{ stats.functional_duplicates }}</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-12">
                    <div class="card visualization">
                        <div class="card-header">Duplication Network</div>
                        <div class="card-body">
                            {{ network_graph_html|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">Structure Insights</div>
                        <div class="card-body">
                            <pre class="code-block">{{ structure_insights }}</pre>
                        </div>
                    </div>
                </div>
            </div>

            <footer>
                <p>Generated with GPU-accelerated analysis {% if use_gpu %}(GPU Enabled){% else %}(CPU Only){% endif %}</p>
                {% if missing_libs %}
                <p>Warning: Some features limited due to missing libraries: {{ missing_libs|join(', ') }}</p>
                {% endif %}
                <p>© 2024 Code Duplication Analyzer</p>
            </footer>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    # Render template
    template = Template(template_str)

    # Safely get structure insights
    structure_insights = "No structure insights available"
    if data and 'structure_insights' in data and data['structure_insights']:
        structure_insights = data['structure_insights']

    # Get report directory with fallback
    report_dir = "."
    if data and 'report_dir' in data and data['report_dir']:
        report_dir = data['report_dir']

    html_content = template.render(
        timestamp=timestamp,
        stats=stats,
        bar_chart_html=bar_chart_html,
        network_graph_html=network_graph_html,
        structure_insights=structure_insights,
        use_gpu=use_gpu,
        missing_libs=missing_libs
    )

    # Write HTML to file
    report_path = os.path.join(report_dir, 'duplication_report.html')
    with open(report_path, 'w') as f:
        f.write(html_content)

    print(f"HTML report generated: {report_path}")
    return report_path

def main():
    """Main function to process duplication report and generate visualizations."""
    parser = argparse.ArgumentParser(description='Generate visualization for code duplication reports')
    parser.add_argument('report_dir', type=str, help='Directory containing duplication reports')
    args = parser.parse_args()

    # Load report data
    data = load_data(args.report_dir)
    if not data:
        print("Failed to load report data")
        return 1

    # Calculate stats
    stats = calculate_summary_stats(data)

    # Create visualizations
    bar_chart_html = create_bar_chart(stats)
    network_graph_html = create_network_graph(data)

    # Generate HTML report
    html_path = generate_html_report(data, stats, bar_chart_html, network_graph_html)

    print(f"Report visualization complete. Open {html_path} to view.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
