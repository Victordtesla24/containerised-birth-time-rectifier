import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';

interface PreferencesState {
  chartStyle: 'north-indian' | 'south-indian' | 'western';
  timeFormat: '12hr' | '24hr';
  showAspects: boolean;
  colorScheme: 'light' | 'dark' | 'custom';
  customColors: {
    background: string;
    text: string;
    houses: string;
    planets: string;
  };
  language: 'en' | 'hi' | 'sa';
}

export default function PreferencesPage() {
  const router = useRouter();
  const [preferences, setPreferences] = useState<PreferencesState>({
    chartStyle: 'north-indian',
    timeFormat: '12hr',
    showAspects: true,
    colorScheme: 'light',
    customColors: {
      background: '#ffffff',
      text: '#000000',
      houses: '#3b82f6',
      planets: '#ef4444',
    },
    language: 'en',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load preferences from localStorage when the component mounts
  useEffect(() => {
    try {
      const storedPreferences = localStorage.getItem('chartPreferences');
      if (storedPreferences) {
        setPreferences(JSON.parse(storedPreferences));
      }
    } catch (err) {
      console.error('Error loading preferences:', err);
    }
  }, []);

  const handleChange = (field: keyof PreferencesState, value: any) => {
    setPreferences(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCustomColorChange = (colorField: keyof PreferencesState['customColors'], value: string) => {
    setPreferences(prev => ({
      ...prev,
      customColors: {
        ...prev.customColors,
        [colorField]: value,
      },
    }));
  };

  const handleSave = () => {
    setIsSaving(true);
    try {
      localStorage.setItem('chartPreferences', JSON.stringify(preferences));
      setSaveMessage({ type: 'success', text: 'Preferences saved successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      console.error('Error saving preferences:', err);
      setSaveMessage({ type: 'error', text: 'Failed to save preferences. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    const defaultPreferences: PreferencesState = {
      chartStyle: 'north-indian',
      timeFormat: '12hr',
      showAspects: true,
      colorScheme: 'light',
      customColors: {
        background: '#ffffff',
        text: '#000000',
        houses: '#3b82f6',
        planets: '#ef4444',
      },
      language: 'en',
    };
    
    setPreferences(defaultPreferences);
    localStorage.setItem('chartPreferences', JSON.stringify(defaultPreferences));
    setSaveMessage({ type: 'success', text: 'Preferences reset to defaults!' });
    setTimeout(() => setSaveMessage(null), 3000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Birth Time Rectifier | Preferences</title>
        <meta name="description" content="Customize your birth chart preferences" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <h1 className="text-3xl font-bold text-center mb-8 text-white">
          Chart Preferences
        </h1>

        <div className="max-w-3xl mx-auto bg-white bg-opacity-90 backdrop-blur-sm rounded-lg shadow p-6">
          <form onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
            {/* Chart Style */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Chart Style</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {['north-indian', 'south-indian', 'western'].map((style) => (
                  <label key={style} className="flex items-center space-x-2">
                    <input
                      type="radio"
                      checked={preferences.chartStyle === style}
                      onChange={() => handleChange('chartStyle', style)}
                      className="h-4 w-4 text-blue-600"
                    />
                    <span className="capitalize">{style.replace('-', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Time Format */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Time Format</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={preferences.timeFormat === '12hr'}
                    onChange={() => handleChange('timeFormat', '12hr')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span>12-hour (AM/PM)</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={preferences.timeFormat === '24hr'}
                    onChange={() => handleChange('timeFormat', '24hr')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span>24-hour</span>
                </label>
              </div>
            </div>

            {/* Display Options */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Display Options</h2>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={preferences.showAspects}
                  onChange={() => handleChange('showAspects', !preferences.showAspects)}
                  className="h-4 w-4 text-blue-600 rounded"
                />
                <span>Show planetary aspects</span>
              </label>
            </div>

            {/* Color Scheme */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Color Scheme</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {['light', 'dark', 'custom'].map((scheme) => (
                  <label key={scheme} className="flex items-center space-x-2">
                    <input
                      type="radio"
                      checked={preferences.colorScheme === scheme}
                      onChange={() => handleChange('colorScheme', scheme)}
                      className="h-4 w-4 text-blue-600"
                    />
                    <span className="capitalize">{scheme}</span>
                  </label>
                ))}
              </div>

              {preferences.colorScheme === 'custom' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  {Object.entries(preferences.customColors).map(([key, value]) => (
                    <div key={key} className="flex items-center">
                      <label className="w-1/3 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}:</label>
                      <input
                        type="color"
                        value={value}
                        onChange={(e) => handleCustomColorChange(key as keyof PreferencesState['customColors'], e.target.value)}
                        className="ml-2"
                      />
                      <span className="ml-2 text-sm text-gray-600">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Language */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold mb-4">Language</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={preferences.language === 'en'}
                    onChange={() => handleChange('language', 'en')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span>English</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={preferences.language === 'hi'}
                    onChange={() => handleChange('language', 'hi')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span>Hindi</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={preferences.language === 'sa'}
                    onChange={() => handleChange('language', 'sa')}
                    className="h-4 w-4 text-blue-600"
                  />
                  <span>Sanskrit</span>
                </label>
              </div>
            </div>

            {/* Save Message */}
            {saveMessage && (
              <div className={`p-4 mb-6 rounded-md ${
                saveMessage.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                {saveMessage.text}
              </div>
            )}

            {/* Buttons */}
            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => router.push('/birth-time-rectifier/analysis')}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
              >
                Back to Analysis
              </button>
              <div className="space-x-4">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                >
                  Reset to Defaults
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className={`px-4 py-2 bg-blue-600 text-white rounded-md ${
                    isSaving ? 'opacity-70 cursor-not-allowed' : 'hover:bg-blue-700'
                  }`}
                >
                  {isSaving ? 'Saving...' : 'Save Preferences'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
} 