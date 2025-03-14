import React from 'react';
import { useRouter } from 'next/router';

/**
 * Simple landing page with very clear "Get Started" button
 * This page is optimized for reliable test interactions
 */
const HomePage = () => {
  const router = useRouter();

  const handleGetStarted = () => {
    // Navigate to the test form page
    router.push('/test-form');
  };

  return (
    <div className="landing-page" style={{
      padding: '40px',
      textAlign: 'center',
      maxWidth: '800px',
      margin: '0 auto',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: '#f0f0f0',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center'
    }}>
      <h1 style={{ fontSize: '2.5rem', marginBottom: '20px' }}>Birth Time Rectifier</h1>
      <p style={{ fontSize: '1.2rem', marginBottom: '40px' }}>
        Discover your precise birth time through astrological analysis
      </p>

      {/* Extra clear button that's easy for tests to find */}
      <button
        data-testid="get-started-button"
        id="get-started-button"
        className="cosmic-button primary"
        onClick={handleGetStarted}
        style={{
          backgroundColor: '#4a90e2',
          color: 'white',
          border: 'none',
          padding: '15px 30px',
          fontSize: '1.2rem',
          borderRadius: '8px',
          cursor: 'pointer',
          margin: '0 auto',
          display: 'block'
        }}
      >
        Get Started
      </button>
    </div>
  );
};

export default HomePage;
