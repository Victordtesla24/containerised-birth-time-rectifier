import { ChartData } from '@/types';
import { jsPDF } from 'jspdf';

export interface ExportOptions {
  width: number;
  height: number;
  format: 'png' | 'svg' | 'pdf';
  filename?: string;
  quality?: number;
}

export const exportChart = async (
  canvas: HTMLCanvasElement,
  data: ChartData,
  options: ExportOptions
): Promise<void> => {
  const filename = options.filename || `birth-chart.${options.format}`;

  switch (options.format) {
    case 'png':
      await exportToPNG(canvas, filename, options.quality);
      break;
    case 'svg':
      await exportToSVG(canvas, data, filename);
      break;
    case 'pdf':
      await exportToPDF(canvas, filename);
      break;
  }
};

const exportToPNG = async (
  canvas: HTMLCanvasElement,
  filename: string,
  quality = 1
): Promise<void> => {
  const link = document.createElement('a');
  link.download = filename;
  link.href = canvas.toDataURL('image/png', quality);
  link.click();
};

interface PathCommand {
  type: 'beginPath' | 'arc' | 'text';
  x?: number;
  y?: number;
  radius?: number;
  text?: string;
}

const exportToSVG = async (
  canvas: HTMLCanvasElement,
  data: ChartData,
  filename: string
): Promise<void> => {
  // Create SVG document
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', canvas.width.toString());
  svg.setAttribute('height', canvas.height.toString());
  svg.setAttribute('viewBox', `0 0 ${canvas.width} ${canvas.height}`);

  // Convert canvas content to SVG
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Since __getPathCommands is not a standard method, we'll need to implement our own path extraction
  const paths = extractPathsFromCanvas(ctx);

  // Convert paths to SVG elements
  paths.forEach((cmd: PathCommand) => {
    switch (cmd.type) {
      case 'beginPath':
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        svg.appendChild(path);
        break;
      case 'arc':
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', cmd.x?.toString() || '');
        circle.setAttribute('cy', cmd.y?.toString() || '');
        circle.setAttribute('r', cmd.radius?.toString() || '');
        svg.appendChild(circle);
        break;
      case 'text':
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', cmd.x?.toString() || '');
        text.setAttribute('y', cmd.y?.toString() || '');
        text.textContent = cmd.text || '';
        svg.appendChild(text);
        break;
    }
  });

  // Convert SVG to string and download
  const svgString = new XMLSerializer().serializeToString(svg);
  const blob = new Blob([svgString], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.download = filename;
  link.href = url;
  link.click();

  URL.revokeObjectURL(url);
};

// Helper function to extract paths from canvas
function extractPathsFromCanvas(ctx: CanvasRenderingContext2D): PathCommand[] {
  // This is a simplified implementation - you'll need to implement proper path extraction
  // based on your specific chart rendering needs
  return [];
}

const exportToPDF = async (
  canvas: HTMLCanvasElement,
  filename: string
): Promise<void> => {
  const pdf = new jsPDF({
    orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
    unit: 'px',
    format: [canvas.width, canvas.height],
  });

  // Add canvas as image to PDF
  const imgData = canvas.toDataURL('image/png', 1.0);
  pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);

  // Save PDF
  pdf.save(filename);
}; 