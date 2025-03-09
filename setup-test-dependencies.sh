#!/bin/bash

# Script to set up all dependencies for the Celestial Visualization testing suite

echo "🔧 Setting up testing dependencies for Celestial Visualization..."

# Install Percy for visual regression testing
echo "📦 Installing Percy for visual regression testing..."
npm install --save-dev @percy/cli @percy/playwright --legacy-peer-deps

# Install performance testing tools
echo "📦 Installing performance testing tools..."
npm install --save-dev lighthouse puppeteer-core chrome-launcher --legacy-peer-deps

# Install additional testing utilities
echo "📦 Installing additional testing utilities..."
npm install --save-dev pixelmatch pngjs canvas --legacy-peer-deps

# Install ts-node and required type definitions
echo "📦 Installing ts-node and type definitions..."
npm install --save-dev ts-node @types/node --legacy-peer-deps

# Create test directories if they don't exist
echo "📁 Creating test directories..."
mkdir -p test-results/screenshots
mkdir -p test-results/videos
mkdir -p test-results/reports

# Set up test pages for component testing
echo "📄 Setting up test pages..."
mkdir -p src/pages/test-pages

# Create test page for CelestialCanvas
cat > src/pages/test-pages/celestial-canvas.tsx << 'EOL'
import React from 'react';
import CelestialCanvas from '../../components/three-scene/CelestialCanvas';

export default function TestCelestialCanvas() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <CelestialCanvas />
    </div>
  );
}
EOL

# Create test page for Sun component
cat > src/pages/test-pages/sun-component.tsx << 'EOL'
import React from 'react';
import { Canvas } from '@react-three/fiber';
import PlanetSystem from '../../components/three-scene/PlanetSystem';

export default function TestSunComponent() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <PlanetSystem showSunOnly={true} />
      </Canvas>
    </div>
  );
}
EOL

# Create test page for Planet component
cat > src/pages/test-pages/planet-component.tsx << 'EOL'
import React from 'react';
import { Canvas } from '@react-three/fiber';
import PlanetSystem from '../../components/three-scene/PlanetSystem';

export default function TestPlanetComponent() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <PlanetSystem showEarthOnly={true} />
      </Canvas>
    </div>
  );
}
EOL

# Create test page for Nebula component
cat > src/pages/test-pages/nebula-component.tsx << 'EOL'
import React from 'react';
import { Canvas } from '@react-three/fiber';
import Nebula from '../../components/three-scene/Nebula';

export default function TestNebulaComponent() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <Nebula />
      </Canvas>
    </div>
  );
}
EOL

# Create test page for EnhancedSpaceScene
cat > src/pages/test-pages/enhanced-space-scene.tsx << 'EOL'
import React from 'react';
import EnhancedSpaceScene from '../../components/visualization/EnhancedSpaceScene';

export default function TestEnhancedSpaceScene() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <EnhancedSpaceScene />
    </div>
  );
}
EOL

# Create test page for PlanetSystem
cat > src/pages/test-pages/planet-system.tsx << 'EOL'
import React from 'react';
import { Canvas } from '@react-three/fiber';
import PlanetSystem from '../../components/three-scene/PlanetSystem';

export default function TestPlanetSystem() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 30], fov: 50 }}>
        <PlanetSystem />
      </Canvas>
    </div>
  );
}
EOL

# Create test page for ShootingStars
cat > src/pages/test-pages/shooting-stars.tsx << 'EOL'
import React from 'react';
import { Canvas } from '@react-three/fiber';
import ShootingStars from '../../components/three-scene/ShootingStars';

export default function TestShootingStars() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: 'black' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <ShootingStars />
      </Canvas>
    </div>
  );
}
EOL

# Create tsconfig.json if it doesn't exist
if [ ! -f tsconfig.json ]; then
  echo "📄 Creating tsconfig.json..."
  cat > tsconfig.json << 'EOL'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "commonjs",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "types": ["node"]
  },
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
EOL
fi

# Update package.json scripts
echo "📝 Updating package.json scripts..."
# This would normally use jq or similar to update package.json
# For now, we'll just print the commands to add

echo "Add these scripts to your package.json:"
echo "  \"test:visual\": \"npx playwright test src/tests/visual-regression\","
echo "  \"test:performance\": \"npx playwright test src/tests/performance\","
echo "  \"test:compatibility\": \"npx playwright test src/tests/compatibility\","
echo "  \"test:interaction\": \"npx playwright test src/tests/interaction\","
echo "  \"test:quality\": \"npx playwright test src/tests/visual-quality\","
echo "  \"test:all\": \"ts-node src/tests/runTests.ts\","
echo "  \"test:report\": \"open test-results/stakeholder-report.html\""

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
npx playwright install

echo "✅ Setup complete! You can now run the tests with:"
echo "  npm run test:all"
echo "  npm run test:visual"
echo "  npm run test:performance"
echo "  npm run test:compatibility"
echo "  npm run test:interaction"
echo "  npm run test:quality"
echo ""
echo "To view the report, run:"
echo "  npm run test:report"
