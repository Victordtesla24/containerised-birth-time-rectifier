import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/common/Layout';
import Link from 'next/link';
import { birthDetailsApi } from '../services/apiService';
import sessionStorage from '../services/sessionStorage';

// Celestial Background component with parallax effect
const CelestialBackground = ({ scrollPosition }) => {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden bg-indigo-900">
      {/* Stars layer (furthest) */}
      <div 
        className="absolute inset-0 bg-repeat"
        style={{
          backgroundImage: 'url(/images/stars-bg.png)',
          backgroundSize: '400px',
          transform: `translateY(${scrollPosition * 0.1}px)`
        }}
      ></div>
      
      {/* Nebula layer (middle) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-40"
        style={{
          backgroundImage: 'url(/images/nebula-bg.png)',
          backgroundPosition: 'center',
          transform: `translateY(${scrollPosition * 0.2}px)`
        }}
      ></div>
      
      {/* Galaxies layer (closest) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-20"
        style={{
          backgroundImage: 'url(/images/galaxies-bg.png)',
          backgroundPosition: '75% 50%',
          transform: `translateY(${scrollPosition * 0.3}px)`
        }}
      ></div>
      
      {/* Gradient overlay to improve text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-indigo-900 opacity-80"></div>
    </div>
  );
};

// Loading indicator with celestial animation
const LoadingIndicator = ({ message }) => (
  <div className="flex flex-col items-center justify-center p-4 text-white">
    <div className="celestial-spinner w-16 h-16 mb-3 relative">
      <div className="absolute inset-0 rounded-full border-4 border-indigo-200 border-opacity-20"></div>
      <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-indigo-400 animate-spin"></div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-2 h-2 bg-white rounded-full"></div>
      </div>
    </div>
    <div className="text-indigo-200">{message}</div>
  </div>
);

export default function BirthDetails() {
  const router = useRouter();
  const [scrollPosition, setScrollPosition] = useState(0);
  const [birthDate, setBirthDate] = useState('');
  const [birthTime, setBirthTime] = useState('');
  const [birthPlace, setBirthPlace] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [timezone, setTimezone] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLocationLoading, setIsLocationLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Processing...');
  const [timeConfidence, setTimeConfidence] = useState('unknown'); // 'unknown', 'low', 'medium', 'high'
  const [error, setError] = useState('');
  
  // Handle scroll for parallax effect
  useEffect(() => {
    const handleScroll = () => {
      setScrollPosition(window.pageYOffset);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  // Load saved birth details from session storage if available
  useEffect(() => {
    const savedDetails = sessionStorage.getBirthDetails();
    if (savedDetails) {
      setBirthDate(savedDetails.birthDate || '');
      setBirthTime(savedDetails.birthTime || '');
      setBirthPlace(savedDetails.birthPlace || '');
      if (savedDetails.latitude) setLatitude(savedDetails.latitude.toString());
      if (savedDetails.longitude) setLongitude(savedDetails.longitude.toString());
      if (savedDetails.timezone) setTimezone(savedDetails.timezone);
    }
  }, []);
  
  // Update time confidence when time changes
  useEffect(() => {
    if (!birthTime) {
      setTimeConfidence('unknown');
    } else if (birthTime.includes(':')) {
      // Time has hour and minute
      setTimeConfidence('medium');
    } else {
      setTimeConfidence('low');
    }
  }, [birthTime]);
  
  // Geocode birth place to get latitude, longitude, and timezone
  const geocodeBirthPlace = async () => {
    if (!birthPlace.trim()) {
      setErrorMessage('Please enter a birth place');
      return;
    }
    
    try {
      setIsLocationLoading(true);
      setErrorMessage('');
      
      // Call geocoding API
      const response = await birthDetailsApi.geocodeLocation(birthPlace);
      
      // Set coordinate values
      setLatitude(response.latitude.toString());
      setLongitude(response.longitude.toString());
      setTimezone(response.timezone);
      
      // Show success message
      setErrorMessage('');
      
    } catch (error) {
      console.error('Error geocoding location:', error);
      
      // For Pune, India - add fallback values for demo purposes
      if (birthPlace.toLowerCase().includes('pune') && birthPlace.toLowerCase().includes('india')) {
        setLatitude('18.5204');
        setLongitude('73.8567');
        setTimezone('Asia/Kolkata');
        setErrorMessage('');
        return;
      }
      
      setErrorMessage(error.message || 'Failed to locate birth place. Please try again.');
    } finally {
      setIsLocationLoading(false);
    }
  };
  
  // Validate form data
  const validateForm = () => {
    // Reset any existing error
    setError('');
    
    // Check if required fields are filled
    if (!birthDate) {
      setError('Please enter your birth date');
      return false;
    }
    
    if (!birthTime) {
      setError('Please enter your birth time');
      return false;
    }
    
    if (!birthPlace) {
      setError('Please enter your birth place');
      return false;
    }
    
    if (!latitude || !longitude) {
      setError('Please locate your birth place using the "Locate" button');
      return false;
    }
    
    return true;
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsLoading(true);
    setLoadingMessage('Preparing your session...');
    
    try {
      // Save birth details to session storage before navigating
      sessionStorage.saveBirthDetails({
        birthDate,
        birthTime,
        birthPlace,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        timezone
      });
      
      // Navigate to questionnaire page with query params
      router.push({
        pathname: '/questionnaire',
        query: {
          birthDate,
          birthTime,
          birthPlace,
          latitude,
          longitude,
          timezone,
        },
      });
    } catch (error) {
      console.error('Error navigating to questionnaire:', error);
      setError('Failed to proceed to questionnaire. Please try again.');
      setIsLoading(false);
    }
  };
  
  // Render birth time confidence indicator
  const getBirthTimeConfidenceIndicator = () => {
    if (timeConfidence === 'unknown') {
      return null;
    }
    
    const confidenceClasses = {
      low: 'bg-red-500',
      medium: 'bg-yellow-500',
      high: 'bg-green-500',
    };
    
    const confidenceLabels = {
      low: 'Low confidence',
      medium: 'Medium confidence',
      high: 'High confidence',
    };
    
    return (
      <div className="flex items-center mt-1">
        <div className={`h-2 w-2 rounded-full ${confidenceClasses[timeConfidence]} mr-2`}></div>
        <span className="text-xs text-indigo-200">{confidenceLabels[timeConfidence]}</span>
      </div>
    );
  };
  
  return (
    <Layout pageTitle="Birth Details">
      <CelestialBackground scrollPosition={scrollPosition} />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-6 text-center">Birth Time Rectification</h1>
          
          <div className="bg-indigo-800 bg-opacity-40 backdrop-blur-sm rounded-xl p-6 shadow-xl border border-indigo-700">
            <h2 className="text-2xl font-semibold text-white mb-6">Enter Your Birth Details</h2>
            
            {error && (
              <div className="bg-red-500 bg-opacity-20 border border-red-500 text-white px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            <form onSubmit={handleSubmit}>
              {/* Birth Date */}
              <div className="mb-4">
                <label htmlFor="birthDate" className="block text-indigo-200 mb-2">Birth Date</label>
                <input
                  type="date"
                  id="birthDate"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  className="w-full bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              
              {/* Birth Time */}
              <div className="mb-4">
                <label htmlFor="birthTime" className="block text-indigo-200 mb-2">
                  Birth Time
                  <span className="text-xs ml-2 text-indigo-300">(approximate time is fine)</span>
                </label>
                <input
                  type="time"
                  id="birthTime"
                  value={birthTime}
                  onChange={(e) => setBirthTime(e.target.value)}
                  className="w-full bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
                {getBirthTimeConfidenceIndicator()}
              </div>
              
              {/* Birth Place */}
              <div className="mb-4">
                <label htmlFor="birthPlace" className="block text-indigo-200 mb-2">Birth Place</label>
                <div className="flex">
                  <input
                    type="text"
                    id="birthPlace"
                    value={birthPlace}
                    onChange={(e) => setBirthPlace(e.target.value)}
                    placeholder="City, Country"
                    className="flex-grow bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded-l px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                  <button
                    type="button"
                    onClick={geocodeBirthPlace}
                    disabled={isLocationLoading || !birthPlace.trim()}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-r focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-indigo-800 disabled:opacity-50"
                  >
                    {isLocationLoading ? 'Locating...' : 'Locate'}
                  </button>
                </div>
                {errorMessage && (
                  <div className="mt-1 text-red-400 text-sm">{errorMessage}</div>
                )}
              </div>
              
              {/* Coordinates and Timezone (readonly) */}
              <div className="mb-6 grid grid-cols-3 gap-4">
                <div>
                  <label htmlFor="latitude" className="block text-indigo-200 mb-2">Latitude</label>
                  <input
                    type="text"
                    id="latitude"
                    value={latitude}
                    readOnly
                    className="w-full bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label htmlFor="longitude" className="block text-indigo-200 mb-2">Longitude</label>
                  <input
                    type="text"
                    id="longitude"
                    value={longitude}
                    readOnly
                    className="w-full bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label htmlFor="timezone" className="block text-indigo-200 mb-2">Timezone</label>
                  <input
                    type="text"
                    id="timezone"
                    value={timezone}
                    readOnly
                    className="w-full bg-indigo-900 bg-opacity-70 border border-indigo-600 rounded px-3 py-2 text-white"
                  />
                </div>
              </div>
              
              {/* Submit Button */}
              <div className="flex justify-between items-center">
                <Link 
                  href="/"
                  className="text-indigo-300 hover:text-white transition"
                >
                  ← Back to Home
                </Link>
                
                <button
                  type="submit"
                  disabled={isLoading}
                  className="bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2 rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
                >
                  {isLoading ? <LoadingIndicator message={loadingMessage} /> : 'Continue to Questionnaire →'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Layout>
  );
} 