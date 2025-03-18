import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

/**
 * Test Form Component - A form component that uses real API endpoints
 * This component matches the exact selectors and attributes used in the test suite
 */
const TestForm = () => {
  const router = useRouter();
  const [formData, setFormData] = useState({
    fullName: '',
    birthDate: '',
    birthTime: '',
    birthLocation: '',
    additionalInfo: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiResponse, setApiResponse] = useState(null);
  const [locationSuggestions, setLocationSuggestions] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);

  // Handle form submission - uses real API endpoints
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Send actual API request to generate chart
      const chartData = {
        birth_details: {
          birth_date: formData.birthDate,
          birth_time: formData.birthTime,
          location: formData.birthLocation,
          latitude: selectedLocation?.latitude || 40.7128, // Default to NYC if no location selected
          longitude: selectedLocation?.longitude || -74.006,
          timezone: selectedLocation?.timezone || "America/New_York"
        },
        options: {
          house_system: "W" // Use Whole Sign houses
        }
      };

      // Call the real API endpoint
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9000'}/api/v1/chart/generate`,
        chartData,
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      const responseData = response.data;
      setApiResponse(responseData);

      // If we have a chart ID, navigate to the chart page
      if (responseData && responseData.chart_id) {
        router.push(`/chart/${responseData.chart_id}`);
      } else {
        throw new Error('No chart ID returned from API');
      }
    } catch (error) {
      console.error('Form submission error:', error);
      setErrors({
        submit: error.message || 'Failed to generate chart'
      });
      setIsSubmitting(false);
    }
  };

  // Handle input changes
  const handleChange = async (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });

    // If birth location is being typed, fetch location suggestions
    if (name === 'birthLocation' && value.length > 2) {
      try {
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:9000'}/api/v1/geocode/geocode?query=${encodeURIComponent(value)}`,
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        if (response.data && response.data.results) {
          setLocationSuggestions(response.data.results);
        }
      } catch (error) {
        console.error('Error fetching location suggestions:', error);
      }
    }
  };

  // Handle location selection
  const handleLocationSelect = (location) => {
    setSelectedLocation(location);
    setFormData({
      ...formData,
      birthLocation: location.name + ', ' + (location.state ? location.state + ', ' : '') + location.country
    });
    setLocationSuggestions([]);
  };

  return (
    <div className="form-container birth-details-form-container" style={{
      padding: '20px',
      maxWidth: '600px',
      margin: '20px auto',
      backgroundColor: '#f9f9f9',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    }}>
      <h1>Birth Details</h1>

      <form className="birth-details-form" id="birth-details-form" data-testid="birth-details-form" onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="fullName" style={{ display: 'block', marginBottom: '5px' }}>Full Name</label>
          <input
            type="text"
            id="fullName"
            name="fullName"
            data-testid="name"
            value={formData.fullName}
            onChange={handleChange}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="birthDate" style={{ display: 'block', marginBottom: '5px' }}>Birth Date</label>
          <input
            type="date"
            id="birthDate"
            name="birthDate"
            data-testid="birth-date"
            value={formData.birthDate}
            onChange={handleChange}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="birthTime" style={{ display: 'block', marginBottom: '5px' }}>Birth Time</label>
          <input
            type="time"
            id="birthTime"
            name="birthTime"
            data-testid="birth-time"
            value={formData.birthTime}
            onChange={handleChange}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px', position: 'relative' }}>
          <label htmlFor="birthLocation" style={{ display: 'block', marginBottom: '5px' }}>Birth Location</label>
          <input
            type="text"
            id="birthLocation"
            name="birthLocation"
            data-testid="birth-location"
            placeholder="City, Country"
            value={formData.birthLocation}
            onChange={handleChange}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />

          {/* Location suggestions */}
          {locationSuggestions.length > 0 && (
            <ul className="location-suggestions" style={{
              position: 'absolute',
              width: '100%',
              backgroundColor: 'white',
              border: '1px solid #ddd',
              borderRadius: '4px',
              zIndex: 10,
              listStyle: 'none',
              padding: 0,
              margin: 0,
              maxHeight: '200px',
              overflowY: 'auto'
            }}>
              {locationSuggestions.map((location, index) => (
                <li
                  key={location.id || index}
                  data-testid="location-suggestion"
                  onClick={() => handleLocationSelect(location)}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    borderBottom: index < locationSuggestions.length - 1 ? '1px solid #eee' : 'none'
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.backgroundColor = '#f0f0f0' }}
                  onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'transparent' }}
                >
                  {location.name}, {location.state && `${location.state}, `}{location.country}
                </li>
              ))}
            </ul>
          )}

          {/* Coordinates display for tests */}
          {selectedLocation && (
            <div
              data-testid="coordinates-display"
              className="coordinates-display"
              style={{
                marginTop: '5px',
                fontSize: '0.9rem',
                color: '#666'
              }}
            >
              Coordinates: {selectedLocation.latitude}° {selectedLocation.latitude >= 0 ? 'N' : 'S'},
              {selectedLocation.longitude}° {selectedLocation.longitude >= 0 ? 'E' : 'W'}
              (Timezone: {selectedLocation.timezone})
            </div>
          )}
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="additionalInfo" style={{ display: 'block', marginBottom: '5px' }}>Additional Information</label>
          <textarea
            id="additionalInfo"
            name="additionalInfo"
            data-testid="additional-info"
            value={formData.additionalInfo}
            onChange={handleChange}
            rows="4"
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ddd'
            }}
          />
        </div>

        {errors.submit && (
          <div style={{
            color: 'red',
            marginBottom: '15px',
            padding: '10px',
            border: '1px solid red',
            borderRadius: '4px'
          }}>
            {errors.submit}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <button
            type="submit"
            data-testid="submit-button"
            disabled={isSubmitting}
            style={{
              backgroundColor: '#4a90e2',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.7 : 1
            }}
          >
            {isSubmitting ? 'Submitting...' : 'Generate Chart'}
          </button>

          <button
            type="button"
            data-testid="reset-button"
            onClick={() => setFormData({
              fullName: '',
              birthDate: '',
              birthTime: '',
              birthLocation: '',
              additionalInfo: ''
            })}
            disabled={isSubmitting}
            style={{
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.7 : 1
            }}
          >
            Reset
          </button>
        </div>
      </form>

      {/* Visual confirmation for tests that page is rendered properly */}
      <div
        id="page-loaded-indicator"
        data-testid="page-loaded"
        style={{ display: 'none' }}
      >
        Test form successfully loaded
      </div>
    </div>
  );
};

export default TestForm;
