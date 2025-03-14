/**
 * D3.js Shim
 *
 * This file provides fallback functionality in case D3.js fails to load properly.
 * It ensures that the application can run even if there are issues with the D3 dependency.
 */

// Create a minimal D3 shim with some basic functionality
const d3Shim = {
  select: (selector: string) => {
    // Basic implementation of d3.select
    const element = typeof document !== 'undefined' ?
      document.querySelector(selector) : null;

    return {
      attr: (name: string, value: any) => {
        if (element && 'setAttribute' in element) {
          element.setAttribute(name, value);
        }
        return d3Shim.select(selector);
      },
      style: (name: string, value: any) => {
        if (element && 'style' in element) {
          (element as any).style[name] = value;
        }
        return d3Shim.select(selector);
      },
      append: (elementType: string) => {
        if (element) {
          const newElement = document.createElement(elementType);
          element.appendChild(newElement);
          return d3Shim.select(`${selector} > ${elementType}:last-child`);
        }
        return d3Shim.select('body');
      },
      selectAll: (childSelector: string) => {
        return d3Shim.selectAll(`${selector} ${childSelector}`);
      },
      text: (value: string) => {
        if (element) {
          element.textContent = value;
        }
        return d3Shim.select(selector);
      },
      html: (value: string) => {
        if (element) {
          element.innerHTML = value;
        }
        return d3Shim.select(selector);
      },
      remove: () => {
        if (element && element.parentNode) {
          element.parentNode.removeChild(element);
        }
        return d3Shim.select('body');
      }
    };
  },

  selectAll: (selector: string) => {
    // Basic implementation of d3.selectAll
    const elements = typeof document !== 'undefined' ?
      document.querySelectorAll(selector) : [];

    return {
      data: (data: any[]) => {
        return {
          enter: () => {
            return {
              append: (elementType: string) => {
                // Simple append implementation
                return d3Shim.selectAll(selector);
              }
            };
          },
          exit: () => {
            return {
              remove: () => {
                // Simple remove implementation
                return d3Shim.selectAll(selector);
              }
            };
          }
        };
      },
      attr: () => d3Shim.selectAll(selector),
      style: () => d3Shim.selectAll(selector),
      text: () => d3Shim.selectAll(selector),
      html: () => d3Shim.selectAll(selector),
      remove: () => d3Shim.selectAll(selector)
    };
  },

  // Scale functions
  scaleLinear: () => {
    return {
      domain: () => d3Shim.scaleLinear(),
      range: () => d3Shim.scaleLinear(),
      nice: () => d3Shim.scaleLinear(),
      // Basic implementation that returns middle of the range
      call: (value: number) => 0.5
    };
  },

  // SVG path generator
  line: () => {
    return {
      x: () => d3Shim.line(),
      y: () => d3Shim.line(),
      defined: () => d3Shim.line(),
      // Returns a straight line
      call: (data: any[]) => "M0,0 L100,100"
    };
  },

  // Dummy transition
  transition: () => {
    return {
      duration: () => d3Shim.transition(),
      delay: () => d3Shim.transition(),
      ease: () => d3Shim.transition()
    };
  }
};

// Try to load the real D3 module, fall back to shim if it fails
let d3: any;

try {
  // Use dynamic import to try loading D3
  d3 = require('d3');
  console.log('Successfully loaded D3.js');
} catch (error) {
  console.warn('Failed to load D3.js, using fallback implementation', error);
  d3 = d3Shim;
}

export default d3;
