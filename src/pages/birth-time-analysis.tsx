import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { BackgroundImage, AnimatedBackgroundImage, useScrollPosition } from '@/components/common/ImageUtils';
import { getRandomImageFromCategory, preloadImages } from '@/utils/imageLoader';
import { motion } from 'framer-motion';
import { CelestialNavbar } from '@/components/common/CelestialNavbar';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';
import { getAllPlanetImagePaths } from '@/utils/planetImages';
import { geocodeBirthplace, geocodeBirthPlace } from '@/services/geocoding';
import { saveBirthDetails } from '@/utils/sessionStorage';

// Form field type
interface FormField {
  name: string;
  type: string;
  label: string;
  placeholder: string;
  required: boolean;
  options?: { value: string; label: string }[];
}

// Birth details form data
interface BirthDetails {
  name: string;
  gender: string;
  birthDate: string;
  approximateTime: string;
  birthLocation: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  timezone?: string;
}

export default function BirthTimeAnalysis() {
  const router = useRouter();
  const scrollPosition = useScrollPosition();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<BirthDetails>({
    name: '',
    gender: '',
    birthDate: '',
    approximateTime: '',
    birthLocation: '',
  });
  const [error, setError] = useState<string | null>(null);

  // Preload background and planet images
  useEffect(() => {
    // Use a specific background image
    const backgroundImage = '/images/backgrounds-2/space-galaxy-1.jpg';

    // Also preload all planet images for better performance in later screens
    const planetImages = getAllPlanetImagePaths();

    // Preload background and planet images
    preloadImages([backgroundImage, ...planetImages])
      .then(() => {
        console.log('Images preloaded successfully');
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error preloading images:', error);
        // Continue even if preloading fails
        setIsLoading(false);
      });
  }, []);

  // Form fields configuration
  const formFields: FormField[] = [
    {
      name: 'name',
      type: 'text',
      label: 'Full Name',
      placeholder: 'Enter your full name',
      required: true
    },
    {
      name: 'gender',
      type: 'select',
      label: 'Gender',
      placeholder: 'Select gender',
      required: true,
      options: [
        { value: 'male', label: 'Male' },
        { value: 'female', label: 'Female' },
        { value: 'non-binary', label: 'Non-binary' },
        { value: 'other', label: 'Other' }
      ]
    },
    {
      name: 'birthDate',
      type: 'date',
      label: 'Birth Date',
      placeholder: 'Select your birth date',
      required: true
    },
    {
      name: 'approximateTime',
      type: 'time',
      label: 'Approximate Birth Time (if known)',
      placeholder: 'HH:MM',
      required: false
    },
    {
      name: 'birthLocation',
      type: 'text',
      label: 'Birth Location',
      placeholder: 'City, Country',
      required: true
    }
  ];

  // Handle form input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Handle form submission
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validate form data
      if (!formData.name.trim()) throw new Error('Please enter your name');
      if (!formData.birthDate) throw new Error('Please enter your birth date');
      if (!formData.approximateTime) throw new Error('Please enter your approximate birth time');
      if (!formData.birthLocation.trim()) throw new Error('Please enter your birth location');

      // Get coordinates for the birth location
      const locationData = await geocodeBirthplace(formData.birthLocation);

      if (!locationData) {
        throw new Error('Could not find coordinates for the entered location. Please try a different city name.');
      }

      // Format the birth details for storage
      const birthDetails = {
        ...formData,
        coordinates: {
          latitude: locationData.latitude,
          longitude: locationData.longitude
        },
        timezone: locationData.timezone || 'UTC'
      };

      // Use the session storage utility to save birth details
      saveBirthDetails({
        name: birthDetails.name,
        gender: birthDetails.gender,
        birthDate: birthDetails.birthDate,
        approximateTime: birthDetails.approximateTime,
        birthLocation: birthDetails.birthLocation,
        coordinates: birthDetails.coordinates,
        timezone: birthDetails.timezone
      });

      console.log('Birth details saved:', birthDetails);

      // Redirect to the questionnaire page
      router.push('/birth-time-rectifier/questionnaire');
    } catch (err) {
      console.error('Error submitting form:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-blue-300 text-lg font-light celestial-text">Loading cosmic imagery...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Birth Time Analysis | Birth Time Rectifier</title>
        <meta name="description" content="Enter your birth details for precise birth time analysis" />
      </Head>

      {/* Canvas-based animated star background */}
      <CelestialBackground />

      {/* Image background with higher z-index than canvas background */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: -5,
        backgroundImage: 'url(/images/backgrounds-2/space-galaxy-1.jpg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        opacity: 0.6,
        mixBlendMode: 'screen'
      }}></div>

      {/* Navbar */}
      <CelestialNavbar />

      <main className="min-h-screen py-12 pt-28">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-2xl mx-auto"
          >
            <div className="text-center mb-10">
              <h1 className="text-4xl font-bold text-white mb-4 high-contrast-text">Birth Time Analysis</h1>
              <p className="text-blue-200">
                Enter your details below to begin your cosmic birth time rectification
              </p>
            </div>

            {/* Form Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="bg-gradient-to-br from-slate-900/90 to-blue-900/30 backdrop-blur-md
                rounded-xl p-8 border border-blue-800/30 shadow-xl chrome-m3-mac"
            >
              {error && (
                <div className="mb-6 p-4 bg-red-900/30 border border-red-500/40 rounded-lg">
                  <p className="text-red-300">{error}</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="celestial-text">
                <div className="space-y-6">
                  {formFields.map((field) => (
                    <div key={field.name} className="space-y-2">
                      <label
                        htmlFor={field.name}
                        className="block text-sm font-medium text-blue-300"
                      >
                        {field.label} {field.required && <span className="text-pink-500">*</span>}
                      </label>

                      {field.type === 'select' ? (
                        <select
                          id={field.name}
                          name={field.name}
                          value={formData[field.name as keyof typeof formData] as string}
                          onChange={handleChange}
                          required={field.required}
                          className="w-full rounded-lg border-blue-800 bg-slate-900/70 text-white
                            focus:ring-blue-500 focus:border-blue-500 py-2 px-3 chrome-m3-mac"
                        >
                          <option value="">{field.placeholder}</option>
                          {field.options?.map(option => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      ) : field.type === 'textarea' ? (
                        <textarea
                          id={field.name}
                          name={field.name}
                          value={formData[field.name as keyof typeof formData] as string}
                          onChange={handleChange}
                          placeholder={field.placeholder}
                          required={field.required}
                          rows={4}
                          className="w-full rounded-lg border-blue-800 bg-slate-900/70 text-white
                            focus:ring-blue-500 focus:border-blue-500 py-2 px-3 chrome-m3-mac"
                        />
                      ) : (
                        <input
                          type={field.type}
                          id={field.name}
                          name={field.name}
                          value={formData[field.name as keyof typeof formData] as string}
                          onChange={handleChange}
                          placeholder={field.placeholder}
                          required={field.required}
                          className="w-full rounded-lg border-blue-800 bg-slate-900/70 text-white
                            focus:ring-blue-500 focus:border-blue-500 py-2 px-3 chrome-m3-mac"
                          autoComplete="on"
                        />
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-10">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="celestial-button w-full disabled:opacity-70 disabled:cursor-not-allowed"
                    type="submit"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <div className="flex items-center justify-center">
                        <span className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        Processing...
                      </div>
                    ) : (
                      "Begin Analysis"
                    )}
                  </motion.button>
                </div>

                <p className="mt-6 text-sm text-blue-300 text-center">
                  Your data is securely processed to determine your precise birth time
                </p>
              </form>
            </motion.div>

            {/* Info Card */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="mt-8 bg-blue-900/20 backdrop-blur-sm rounded-lg p-4 border border-blue-800/20"
            >
              <h3 className="text-sm font-semibold text-blue-300 mb-2">How it works:</h3>
              <ul className="text-sm text-blue-200 space-y-1 list-disc pl-5">
                <li>Enter your birth details in the form above</li>
                <li>Complete our specialized questionnaire about key life events</li>
                <li>Our algorithm analyzes your cosmic pattern and key life transitions</li>
                <li>Advanced celestial pattern matching refines your birth time</li>
                <li>Receive your precise birth time analysis in just moments</li>
              </ul>
            </motion.div>
          </motion.div>
        </div>
      </main>
    </>
  );
}
