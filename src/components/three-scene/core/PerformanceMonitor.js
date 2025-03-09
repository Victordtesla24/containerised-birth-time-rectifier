/**
 * PerformanceMonitor
 * Monitors WebGL rendering performance and provides suggestions for quality adjustments
 */
class PerformanceMonitor {
  constructor(options = {}) {
    this.options = {
      sampleSize: 30, // Number of frames to collect for FPS calculation
      targetFps: 60, // Target frame rate
      warningThreshold: 30, // FPS threshold to trigger a warning
      criticalThreshold: 20, // FPS threshold for critical performance issues
      updateInterval: 1000, // Interval for performance checks (ms)
      onQualitySuggestion: null, // Callback when quality changes are suggested
      ...options
    };

    this.isRunning = false;
    this.fpsSamples = [];
    this.lastTime = 0;
    this.frameCount = 0;
    this.lastUpdateTime = 0;
    this.lastSuggestionTime = 0;
    this.currentFps = 0;
    this.smoothedFps = 0;
    this.qualityLevel = 'high'; // initial quality: high, medium, low

    // Performance suggestion cooldown (avoid too frequent changes)
    this.suggestionCooldown = 5000; // 5 seconds between quality suggestions
  }

  /**
   * Start monitoring performance
   */
  start() {
    if (this.isRunning) return;

    this.isRunning = true;
    this.lastTime = performance.now();
    this.lastUpdateTime = this.lastTime;
    this.lastSuggestionTime = 0;
    this.frameCount = 0;
    this.fpsSamples = [];
    this.qualityLevel = 'high';
  }

  /**
   * Stop monitoring performance
   */
  stop() {
    this.isRunning = false;
  }

  /**
   * Calculate current FPS
   * @param {number} now - Current timestamp
   * @returns {number} Current FPS
   */
  calculateFps(now) {
    const delta = now - this.lastTime;
    this.lastTime = now;

    // Calculate instantaneous FPS (limit to reasonable range to avoid spikes)
    const fps = delta > 0 ? Math.min(1000 / delta, 120) : 0;

    // Add to samples array
    this.fpsSamples.push(fps);

    // Keep only the most recent samples
    if (this.fpsSamples.length > this.options.sampleSize) {
      this.fpsSamples.shift();
    }

    // Calculate average FPS from samples
    const totalFps = this.fpsSamples.reduce((sum, value) => sum + value, 0);
    return this.fpsSamples.length > 0 ? totalFps / this.fpsSamples.length : 0;
  }

  /**
   * Check if quality suggestions should be generated
   * @param {number} now - Current timestamp
   * @param {number} fps - Current FPS
   * @returns {boolean} Whether suggestions should be made
   */
  shouldSuggestQuality(now, fps) {
    // Don't suggest until we have enough samples
    if (this.fpsSamples.length < this.options.sampleSize) {
      return false;
    }

    // Only suggest after cooldown period
    if (now - this.lastSuggestionTime < this.suggestionCooldown) {
      return false;
    }

    // Check if FPS is below thresholds
    return (
      fps < this.options.criticalThreshold ||
      (fps < this.options.warningThreshold && this.qualityLevel !== 'low')
    );
  }

  /**
   * Generate quality suggestions based on performance
   * @param {number} fps - Current FPS
   * @returns {Object} Quality suggestions
   */
  generateQualitySuggestions(fps) {
    let newQualityLevel = this.qualityLevel;

    if (fps < this.options.criticalThreshold) {
      newQualityLevel = 'low';
    } else if (fps < this.options.warningThreshold) {
      newQualityLevel = this.qualityLevel === 'high' ? 'medium' : 'low';
    }

    // Only return if quality needs to change
    if (newQualityLevel === this.qualityLevel) {
      return null;
    }

    this.qualityLevel = newQualityLevel;

    // Generate specific quality suggestions based on level
    const suggestions = {
      qualityLevel: newQualityLevel,
      // Specific settings to adjust
      antialias: newQualityLevel !== 'low',
      shadows: newQualityLevel === 'high',
      pixelRatio: newQualityLevel === 'high' ? window.devicePixelRatio :
                 newQualityLevel === 'medium' ? Math.min(window.devicePixelRatio, 1.5) : 1,
      particleCount: newQualityLevel === 'high' ? 1 :
                    newQualityLevel === 'medium' ? 0.6 : 0.3, // Multiplier
      textureQuality: newQualityLevel === 'high' ? 'high' :
                     newQualityLevel === 'medium' ? 'medium' : 'low',
    };

    return suggestions;
  }

  /**
   * Update the performance monitor
   * Called each frame from the render loop
   * @param {THREE.WebGLRenderer} renderer - The WebGL renderer
   */
  update(renderer) {
    if (!this.isRunning) return;

    const now = performance.now();
    this.frameCount++;

    // Calculate FPS
    this.currentFps = this.calculateFps(now);

    // Check if it's time for a performance update
    if (now - this.lastUpdateTime > this.options.updateInterval) {
      this.smoothedFps = this.currentFps;
      this.lastUpdateTime = now;

      // Get rendering stats if available
      const stats = renderer ? renderer.info : null;

      // Check if we should suggest quality changes
      if (this.shouldSuggestQuality(now, this.smoothedFps)) {
        const suggestions = this.generateQualitySuggestions(this.smoothedFps);

        if (suggestions && typeof this.options.onQualitySuggestion === 'function') {
          // Pass performance metrics along with suggestions
          this.options.onQualitySuggestion({
            fps: this.smoothedFps,
            targetFps: this.options.targetFps,
            frameCount: this.frameCount,
            renderStats: stats,
            suggestions
          });

          this.lastSuggestionTime = now;
        }
      }
    }
  }

  /**
   * Get current performance metrics
   * @returns {Object} Performance metrics
   */
  getMetrics() {
    return {
      fps: this.smoothedFps,
      quality: this.qualityLevel,
      isRunning: this.isRunning,
      targetFps: this.options.targetFps,
      sampleCount: this.fpsSamples.length
    };
  }
}

export default PerformanceMonitor;
