#!/bin/bash

# Check TypeScript types for visualization components
echo "🔍 Checking TypeScript types for visualization components..."

# Check if src/components/visualization/tsconfig.json exists
if [ ! -f "src/components/visualization/tsconfig.json" ]; then
  echo "Creating visualization-specific tsconfig.json..."
  mkdir -p src/components/visualization
  cat > src/components/visualization/tsconfig.json << EOF
{
  "extends": "../../../tsconfig.json",
  "include": [
    "**/*.ts",
    "**/*.tsx"
  ],
  "compilerOptions": {
    "noEmit": true,
    "skipLibCheck": true
  }
}
EOF
fi

# Run TypeScript check with the visualization-specific tsconfig
echo "Running TypeScript check for visualization components..."
npx tsc --project src/components/visualization/tsconfig.json

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ TypeScript check passed for visualization components!"
  exit 0
else
  echo "❌ TypeScript check failed for visualization components."
  echo "🔧 Run ./scripts/fix-typescript.sh to fix type issues."
  exit 1
fi
