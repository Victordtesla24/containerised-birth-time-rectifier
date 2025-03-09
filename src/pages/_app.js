import React from 'react';
import Head from 'next/head';
import { QualityProvider } from '../components/providers/QualityProvider';
import { SessionProvider } from '../components/providers/SessionProvider';
import ErrorBoundary from '@/components/ErrorBoundary';

import '../styles/globals.css';

/**
 * Custom App component with QualityProvider for adaptive rendering,
 * SessionProvider for session management, and global error handling
 */
function MyApp({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>Birth Time Rectifier</title>
        <meta name="description" content="Astrological birth time rectification using celestial calculations" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <ErrorBoundary>
        <SessionProvider>
          <QualityProvider>
            <Component {...pageProps} />
          </QualityProvider>
        </SessionProvider>
      </ErrorBoundary>
    </>
  );
}

export default MyApp;
