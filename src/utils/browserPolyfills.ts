/**
 * Browser compatibility polyfills and feature detection
 * This file helps ensure consistent behavior across different browsers,
 * particularly for Safari on macOS and iOS, and Chrome on M3 Macs
 */

const checkBrowserSupport = () => {
  // Check browser support for various CSS features
  const supportCheck = {
    mixBlendMode: CSS.supports('mix-blend-mode', 'screen'),
    backdropFilter: CSS.supports('backdrop-filter', 'blur(10px)'),
    webpSupport: false,
    fontVariationSettings: CSS.supports('font-variation-settings', '"wght" 400'),
    isChrome: false,
    isM3Mac: false
  };

  // Check WebP support
  const canvas = document.createElement('canvas');
  if (canvas.getContext && canvas.getContext('2d')) {
    // If browser supports canvas, check WebP support
    supportCheck.webpSupport = canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
  }

  // Detect Chrome browser
  const ua = navigator.userAgent.toLowerCase();
  supportCheck.isChrome = ua.indexOf('chrome') !== -1;
  
  // Check if running on ARM64 architecture (M-series Macs)
  supportCheck.isM3Mac = ua.indexOf('arm64') !== -1 || ua.indexOf('macOS') !== -1;

  return supportCheck;
};

// Apply browser-specific fixes
export const applyBrowserFixes = () => {
  const support = checkBrowserSupport();
  
  if (!support.mixBlendMode) {
    // Add fallback class to body if mix-blend-mode isn't supported
    document.body.classList.add('no-blend-mode-support');
  }
  
  if (!support.backdropFilter) {
    // Add fallback class for backdrop-filter
    document.body.classList.add('no-backdrop-filter-support');
  }

  // Safari specific fixes for font rendering
  const ua = navigator.userAgent.toLowerCase();
  if (ua.indexOf('safari') !== -1 && ua.indexOf('chrome') === -1) {
    document.body.classList.add('safari-browser');
    
    // Add extra contrast to text elements in dark backgrounds
    const styleSheet = document.createElement('style');
    styleSheet.innerText = `
      .text-white, .text-blue-300, .text-blue-200 {
        text-shadow: 0 0 1px rgba(0,0,0,0.8);
        letter-spacing: 0.01em;
      }
    `;
    document.head.appendChild(styleSheet);
  }

  // Chrome on M3 Mac specific optimizations
  if (support.isChrome && support.isM3Mac) {
    document.body.classList.add('chrome-m3-mac');
    
    // Add specific styles for Chrome on M3 Macs
    const chromeM3Styles = document.createElement('style');
    chromeM3Styles.innerText = `
      /* Hardware acceleration for smoother animations on M3 Mac */
      .celestial-body, .animate-spin, .celestial-rotate, .celestial-rotate-slow, .celestial-rotate-fast {
        transform: translateZ(0);
        will-change: transform;
        backface-visibility: hidden;
      }
      
      /* Better button rendering for Chrome on M3 */
      button, .celestial-button {
        -webkit-appearance: none;
        appearance: none;
        transform: translateZ(0);
      }
      
      /* Improve text rendering */
      .celestial-text, .high-contrast-text {
        -webkit-font-smoothing: antialiased;
        font-synthesis: none;
        text-rendering: optimizeLegibility;
      }
      
      /* Fix for flickering transitions in Chrome on M3 */
      .transition-all {
        backface-visibility: hidden;
        perspective: 1000px;
      }
    `;
    document.head.appendChild(chromeM3Styles);
  }
};

export default applyBrowserFixes; 