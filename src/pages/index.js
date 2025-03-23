import React from 'react';

export default function Home() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem',
      backgroundColor: '#f7f7f7'
    }}>
      <h1 style={{
        fontSize: '2.5rem',
        marginBottom: '1rem',
        color: '#333'
      }}>
        Birth Time Rectifier
      </h1>
      <p style={{
        fontSize: '1.2rem',
        maxWidth: '800px',
        textAlign: 'center',
        color: '#555'
      }}>
        Welcome to the Birth Time Rectifier application. This tool helps users determine accurate birth times for astrological chart creation.
      </p>
      <div style={{
        marginTop: '2rem'
      }}>
        <a href="/api/health" style={{
          padding: '0.75rem 1.5rem',
          backgroundColor: '#4a90e2',
          color: 'white',
          borderRadius: '4px',
          textDecoration: 'none',
          fontWeight: 'bold'
        }}>
          Check API Health
        </a>
      </div>
    </div>
  );
}
