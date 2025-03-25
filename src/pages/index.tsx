import React from 'react';
import Head from 'next/head';
import { PlanetaryVisualization } from '../components/charts/PlanetaryVisualization';
import { Planet } from '../types/astrology';

// Sample planets data for visualization
const samplePlanets: Planet[] = [
  {
    id: 'sun',
    name: 'Sun',
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: 1.5,
    color: '#FFD700',
    symbol: '☉'
  },
  {
    id: 'moon',
    name: 'Moon',
    position: { x: 3, y: 1, z: 0.5 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: 1.2,
    color: '#E6E6FA',
    symbol: '☽'
  },
  {
    id: 'mercury',
    name: 'Mercury',
    position: { x: -2, y: 2, z: 0.3 },
    rotation: { x: 0, y: 0, z: Math.PI / 4 },
    scale: 0.8,
    color: '#B5B5B5',
    symbol: '☿'
  },
  {
    id: 'venus',
    name: 'Venus',
    position: { x: 2, y: -1.5, z: 0.2 },
    rotation: { x: 0, y: 0, z: -Math.PI / 6 },
    scale: 1.1,
    color: '#FFB6C1',
    symbol: '♀'
  },
  {
    id: 'mars',
    name: 'Mars',
    position: { x: -3, y: -2, z: 0.4 },
    rotation: { x: 0, y: 0, z: Math.PI / 3 },
    scale: 0.9,
    color: '#FF4500',
    symbol: '♂'
  },
  {
    id: 'jupiter',
    name: 'Jupiter',
    position: { x: 4, y: 3, z: 0.1 },
    rotation: { x: 0, y: 0, z: -Math.PI / 5 },
    scale: 1.8,
    color: '#F4A460',
    symbol: '♃'
  },
  {
    id: 'saturn',
    name: 'Saturn',
    position: { x: -4, y: 3.5, z: 0.2 },
    rotation: { x: 0, y: 0, z: Math.PI / 7 },
    scale: 1.6,
    color: '#DAA520',
    symbol: '♄'
  }
];

export default function Home() {
  return (
    <div className="container">
      <Head>
        <title>Birth Time Rectifier</title>
        <meta name="description" content="Precise birth time rectification using advanced astrological techniques" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="main">
        <h1 className="title">
          Birth Time Rectifier
        </h1>

        <p className="description">
          Precise birth time rectification using advanced astrological techniques
        </p>

        <div className="visualization-container">
          <h2>Planetary Positions</h2>
          <PlanetaryVisualization planets={samplePlanets} />
        </div>
      </main>

      <footer className="footer">
        <p>Powered by advanced astrological algorithms</p>
      </footer>

      <style jsx>{`
        .container {
          min-height: 100vh;
          padding: 0 2rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
        }

        .main {
          padding: 4rem 0;
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          width: 100%;
          max-width: 1200px;
        }

        .footer {
          width: 100%;
          height: 100px;
          border-top: 1px solid var(--surface-color);
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .title {
          margin: 0;
          line-height: 1.15;
          font-size: 4rem;
          text-align: center;
          color: var(--primary-color);
        }

        .description {
          margin: 2rem 0;
          line-height: 1.5;
          font-size: 1.5rem;
          text-align: center;
          color: var(--text-secondary-color);
        }

        .visualization-container {
          width: 100%;
          margin-top: 2rem;
        }

        .visualization-container h2 {
          margin-bottom: 1rem;
          color: var(--secondary-color);
        }
      `}</style>
    </div>
  );
}
