/**
 * WebGLContextHandler
 * Manages WebGL context loss and restoration events
 */
class WebGLContextHandler {
  constructor(renderer) {
    this.renderer = renderer;
    this.canvas = renderer.domElement;
    this.eventListeners = {};
    this.contextLost = false;

    this.initialize();
  }

  initialize() {
    // Listen for context lost and restored events
    this.canvas.addEventListener('webglcontextlost', this.handleContextLost.bind(this), false);
    this.canvas.addEventListener('webglcontextrestored', this.handleContextRestored.bind(this), false);
  }

  /**
   * Handle WebGL context loss event
   * @param {Event} event - The context lost event
   */
  handleContextLost(event) {
    // Prevent default to allow for context restoration
    event.preventDefault();

    this.contextLost = true;

    console.warn('WebGL context lost');

    // Notify all listeners
    this.emit('contextLost', event);
  }

  /**
   * Handle WebGL context restoration event
   * @param {Event} event - The context restored event
   */
  handleContextRestored(event) {
    this.contextLost = false;

    console.info('WebGL context restored');

    // Recreate renderer capabilities and state
    // Note: Three.js handles most of this internally
    if (this.renderer) {
      this.renderer.info.reset();
    }

    // Notify all listeners
    this.emit('contextRestored', event);
  }

  /**
   * Attempt to manually restore the context
   * This is not guaranteed to work and depends on browser implementation
   */
  manualRestore() {
    if (!this.contextLost) return;

    // Some browsers allow extensions to restore context
    try {
      // Try to get WebGL lose_context extension
      const gl = this.renderer.getContext();
      const ext = gl && gl.getExtension('WEBGL_lose_context');

      if (ext) {
        console.info('Attempting manual WebGL context restoration');
        ext.restoreContext();
        return true;
      }
    } catch (error) {
      console.error('Failed manual context restore:', error);
    }

    return false;
  }

  /**
   * Register an event listener for a specific event
   * @param {string} event - The event to listen for ('contextLost' or 'contextRestored')
   * @param {Function} callback - The callback function to execute
   */
  on(event, callback) {
    if (!this.eventListeners[event]) {
      this.eventListeners[event] = [];
    }

    this.eventListeners[event].push(callback);
  }

  /**
   * Remove an event listener for a specific event
   * @param {string} event - The event type
   * @param {Function} callback - The callback function to remove
   */
  off(event, callback) {
    if (!this.eventListeners[event]) return;

    this.eventListeners[event] = this.eventListeners[event].filter(
      listener => listener !== callback
    );
  }

  /**
   * Emit an event to all registered listeners
   * @param {string} event - The event type to emit
   * @param {*} data - Data to pass to event listeners
   */
  emit(event, data) {
    if (!this.eventListeners[event]) return;

    this.eventListeners[event].forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${event} listener:`, error);
      }
    });
  }

  /**
   * Clean up event listeners and references
   */
  dispose() {
    if (this.canvas) {
      this.canvas.removeEventListener('webglcontextlost', this.handleContextLost);
      this.canvas.removeEventListener('webglcontextrestored', this.handleContextRestored);
    }

    this.eventListeners = {};
    this.renderer = null;
    this.canvas = null;
  }
}

export default WebGLContextHandler;
