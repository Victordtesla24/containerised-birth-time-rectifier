// Forward exports from the modularized shootingStars components
import ShootingStarsComponent from './shootingStars/ShootingStars.jsx';

// Re-export the ShootingStars component as the default export
export default ShootingStarsComponent;

// Also export the individual shootingStar component to maintain backward compatibility
export { ShootingStar } from './shootingStars/index.jsx';
