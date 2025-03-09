# Visualization Components

This directory contains all visualization components for the application, organized into a structured directory layout for better separation of concerns and maintainability.

## Directory Structure

- `canvas/` - Canvas-based 2D visualizations
- `three/` - Three.js-based 3D visualizations
- `common/` - Shared components and utilities used by both implementations

## Key Components

### Main Visualization Adapter

The `VisualizationAdapter` component automatically selects the appropriate visualization implementation based on device capabilities:

```jsx
import { CelestialVisualization } from '../components/visualization';

// It will automatically use Three.js or Canvas based on the device capabilities
<CelestialVisualization />
```

### Specific Implementations

If you need to use a specific implementation, you can import them directly:

```jsx
import { CanvasVisualization, ThreeJsVisualization } from '../components/visualization';

// Canvas-based implementation
<CanvasVisualization />

// Three.js-based implementation
<ThreeJsVisualization />
```

### Common Components

These components can be used independently for specific UI elements:

```jsx
import { ConfidenceMeter, CelestialChart } from '../components/visualization';

<ConfidenceMeter value={75} />
<CelestialChart planetPositions={data} />
```

## Quality Settings

The Three.js implementation supports different quality levels:

- `low` - For low-end devices
- `medium` - For average devices
- `high` - For high-end devices
- `ultra` - For powerful desktop computers

```jsx
<CelestialVisualization quality="high" />
```

## Customization Properties

All visualization components accept the following props:

- `enableShootingStars` - Enable/disable shooting stars (default: true)
- `enableOrbits` - Enable/disable orbital paths (default: true)
- `enableNebulaEffects` - Enable/disable nebula effects (default: true)
- `mouseInteractive` - Enable/disable mouse interactivity (default: true)
- `quality` - Set quality level ('low', 'medium', 'high', 'ultra')
- `particleCount` - Override default particle count
