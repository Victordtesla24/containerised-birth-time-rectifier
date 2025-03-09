# Project Technical State

## Project Structure
- Frontend: Next.js application with React components
- Backend: AI service built with Python/FastAPI
- Database: Redis for caching and data storage

## Frontend Visualization Components

### Three.js Components (Updated March 7, 2025)

#### Modular Architecture
The visualization components have been refactored to improve maintainability and performance:

1. **Nebula Component** - Split into modular components:
   - `src/components/three-scene/nebula/Nebula.jsx` - Core component implementation
   - `src/components/three-scene/nebula/NebulaMaterial.jsx` - Material creation logic
   - `src/components/three-scene/nebula/NebulaShaders.jsx` - GLSL shader code
   - `src/components/three-scene/nebula/index.jsx` - Export management
   - Legacy `src/components/three-scene/Nebula.jsx` - Forwards to new structure

2. **ShootingStars Component** - Split into modular components:
   - `src/components/three-scene/shootingStars/ShootingStars.jsx` - Main component
   - `src/components/three-scene/shootingStars/ShootingStar.jsx` - Individual star implementation
   - `src/components/three-scene/shootingStars/index.jsx` - Export management
   - Legacy `src/components/three-scene/ShootingStars.jsx` - Forwards to new structure

3. **Shared Utilities**:
   - `src/components/three-scene/utils/ShaderUtils.jsx` - Reusable shader functions
   - `src/components/three-scene/utils/TextureLoader.jsx` - Texture loading with error handling

4. **Components for Future Modularization**:
   - `src/components/three-scene/CelestialCanvas.jsx` - Main canvas component
   - `src/components/three-scene/PlanetSystem.jsx` - Planet rendering system

#### Optimization Techniques Applied
Based on Perplexity AI recommendations (documented in `docs/threejs-optimization-recommendations.md`):

1. **Geometry Optimization**
   - Using BufferGeometry with typed arrays
   - Proper disposal of geometries with cleanup functions

2. **Shader Performance**
   - Early discard in fragment shaders for transparent areas
   - Reduced branching in shader code
   - Vertex shader optimizations

3. **Texture Management**
   - Proper texture loading with error handling
   - Fallback texture generation
   - Memory management with proper disposal

4. **Adaptive Quality**
   - Device capability detection
   - Quality-based rendering settings
   - Dynamic adjustment of detail levels

5. **Error Handling**
   - Graceful fallbacks for missing assets
   - Error prevention in rendering pipeline

## API Integration

The application integrates with several APIs:

1. **Internal API Endpoints**:
   - `/api/birth-chart` - Generates birth charts based on date/time/location
   - `/api/rectification` - Performs birth time rectification algorithms
   - `/api/prediction` - Provides astrological predictions

2. **External API Integration**:
   - Swiss Ephemeris for planetary calculations
   - GeoNames API for location data

## Performance Considerations

1. **Visualization Performance**:
   - Implemented adaptive rendering quality based on device
   - Optimized shader code for better GPU utilization
   - Added progressive loading for assets

2. **API Performance**:
   - Redis caching for ephemeris calculations
   - Batched API requests for performance

## Future Technical Improvements

1. **Visualization Components**:
   - Further modularize `CelestialCanvas.jsx` and `PlanetSystem.jsx`
   - Implement additional Three.js performance optimizations from Perplexity research
   - Add comprehensive unit tests for visualization modules

2. **API and Data Flow**:
   - Implement server-side rendering for faster initial load
   - Add WebSocket support for real-time updates
   - Optimize data transfer between frontend and backend

3. **Build and Deployment**:
   - Optimize bundle size with code splitting
   - Implement automated performance regression testing
   - Enhance containerization for better scaling
