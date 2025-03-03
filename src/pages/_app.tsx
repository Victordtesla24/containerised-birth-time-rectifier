import '../styles/globals.css';
import '../styles/celestial.css';
import type { AppProps } from 'next/app';
import ErrorBoundary from '@/components/ErrorBoundary';
import Head from 'next/head';
import { useEffect } from 'react';
import { applyBrowserFixes } from '@/utils/browserPolyfills';

function MyApp({ Component, pageProps }: AppProps) {
  // Apply browser compatibility fixes on client side
  useEffect(() => {
    applyBrowserFixes();
  }, []);

  return (
    <ErrorBoundary>
      <Head>
        {/* Essential meta tags for better browser compatibility */}
        <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="color-scheme" content="dark" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="theme-color" content="#000830" />
        
        {/* Force text rendering optimization on all browsers */}
        <style>
          {`
            * {
              text-rendering: optimizeLegibility;
              -webkit-font-smoothing: antialiased;
              -moz-osx-font-smoothing: grayscale;
            }
            
            body {
              margin: 0;
              padding: 0;
              font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
              background-color: #000000;
              color: #ffffff;
            }
            
            .basic-text {
              color: #ffffff;
              text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
            }
            
            .container {
              width: 100%;
              max-width: 1280px;
              margin: 0 auto;
              padding: 0 16px;
            }
          `}
        </style>
      </Head>
      
      <div className="basic-text celestial-text">
        <Component {...pageProps} />
      </div>
    </ErrorBoundary>
  );
}

export default MyApp; 