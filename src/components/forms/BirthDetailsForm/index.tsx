import React, { useState, useEffect, useCallback } from 'react';
import { BirthDetailsFormProps, FormState, ValidationErrors } from './types';
import { validateBirthDetails, hasErrors } from './validation';
import { format, parse } from 'date-fns';
import { geocodeBirthPlace } from '@/services/geocoding';
import { BirthDetails } from '@/types';

const BirthDetailsForm: React.FC<BirthDetailsFormProps> = ({
  onSubmit,
  onValidation,
  initialData,
  isLoading = false
}) => {
  const [formData, setFormData] = useState<FormState>({
    date: initialData?.birthDate || '',
    time: initialData?.approximateTime || '',
    birthPlace: initialData?.birthLocation || '',
    latitude: initialData?.coordinates?.latitude || 0,
    longitude: initialData?.coordinates?.longitude || 0,
    timezone: initialData?.timezone || '',
  });

  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [locationVerified, setLocationVerified] = useState(false);

  // Handle field touch state
  const handleFieldTouch = useCallback((field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }));
  }, []);

  // Validate on change and touch
  useEffect(() => {
    const validationErrors = validateBirthDetails(formData);
    setErrors(validationErrors);
    onValidation(!hasErrors(validationErrors));
  }, [formData, onValidation]);

  // Geocode birth place when it changes
  useEffect(() => {
    let isMounted = true;
    let timeoutId: NodeJS.Timeout;

    const geocodeLocation = async () => {
      if (formData.birthPlace && formData.birthPlace.length >= 3 && touched.birthPlace) {
        setIsGeocoding(true);
        setLocationVerified(false);

        // Clear previous error messages first
        setErrors(prev => ({
          ...prev,
          birthPlace: undefined,
          submit: undefined
        }));

        try {
          const { latitude, longitude, timezone } = await geocodeBirthPlace(formData.birthPlace);
          if (isMounted) {
            setFormData(prev => ({
              ...prev,
              latitude,
              longitude,
              timezone,
            }));
            setLocationVerified(true);
          }
        } catch (error) {
          if (isMounted) {
            console.error("Geocoding failed:", error);
            setErrors(prev => ({
              ...prev,
              birthPlace: 'Could not find this location. Please check the spelling.',
            }));

            // Clear the coordinate data on geocoding failure
            setFormData(prev => ({
              ...prev,
              latitude: 0,
              longitude: 0,
              timezone: '',
            }));
            setLocationVerified(false);
          }
        } finally {
          if (isMounted) {
            setIsGeocoding(false);
          }
        }
      } else if (formData.birthPlace.length < 3 && touched.birthPlace) {
        // Clear coordinate data when birth place is too short
        setFormData(prev => ({
          ...prev,
          latitude: 0,
          longitude: 0,
          timezone: '',
        }));
        setLocationVerified(false);
      }
    };

    // Debounce the geocoding to avoid unnecessary API calls
    timeoutId = setTimeout(geocodeLocation, 800);

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
  }, [formData.birthPlace, touched.birthPlace]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationErrors = validateBirthDetails(formData);
    setErrors(validationErrors);
    setTouched(Object.keys(formData).reduce((acc, key) => ({ ...acc, [key]: true }), {}));

    // Prevent submission if geocoding is in progress
    if (isGeocoding) {
      setErrors(prev => ({
        ...prev,
        submit: 'Please wait for location geocoding to complete',
      }));
      return;
    }

    // Check if location data is valid before proceeding
    if (!formData.latitude || !formData.longitude || !formData.timezone) {
      // If birth place is provided but coordinates are missing, try geocoding again
      if (formData.birthPlace && formData.birthPlace.length >= 3) {
        setErrors(prev => ({
          ...prev,
          submit: 'Location data is not available. Please try again or enter a different location.',
        }));

        // Attempt to geocode again
        try {
          setIsGeocoding(true);
          const { latitude, longitude, timezone } = await geocodeBirthPlace(formData.birthPlace);
          setFormData(prev => ({
            ...prev,
            latitude,
            longitude,
            timezone,
          }));
          setIsGeocoding(false);
          setLocationVerified(true);

          // Don't submit yet - let user try again after data is fetched
          return;
        } catch (error) {
          setIsGeocoding(false);
          setLocationVerified(false);
          setErrors(prev => ({
            ...prev,
            birthPlace: 'Could not find this location. Please check the spelling.',
            submit: 'Location information is missing. Please enter a valid birth place.',
          }));
          return;
        }
      } else {
        setErrors(prev => ({
          ...prev,
          birthPlace: 'Birth place is invalid or missing',
          submit: 'Location information is missing. Please enter a valid birth place.',
        }));
        return;
      }
    }

    if (!hasErrors(validationErrors)) {
      try {
        // Parse the date string to ensure correct format
        const dateObj = parse(formData.date, 'yyyy-MM-dd', new Date());

        // Ensure time is in 24-hour format (HH:MM)
        let time = formData.time;

        // If time contains AM/PM, convert it to 24-hour format
        if (time.toLowerCase().includes('am') || time.toLowerCase().includes('pm')) {
          const isPM = time.toLowerCase().includes('pm');
          // Extract hours and minutes, removing AM/PM
          const timeParts = time.toLowerCase().replace(/(am|pm)/i, '').trim().split(':');
          let hours = parseInt(timeParts[0]);
          const minutes = timeParts[1] || '00';

          // Convert to 24-hour format
          if (isPM && hours < 12) {
            hours += 12;
          } else if (!isPM && hours === 12) {
            hours = 0;
          }

          // Format time as HH:MM
          time = `${hours.toString().padStart(2, '0')}:${minutes}`;
        }

        // Create birth details object matching the expected structure
        const birthDetails: BirthDetails = {
          name: '',
          gender: '', // Default empty as it's not collected in this form
          birthDate: format(dateObj, 'yyyy-MM-dd'),
          approximateTime: time,
          birthLocation: formData.birthPlace,
          coordinates: {
            latitude: formData.latitude || 0,
            longitude: formData.longitude || 0
          },
          timezone: formData.timezone || '',
        };

        await onSubmit(birthDetails);
      } catch (error) {
        console.error('Form submission error:', error);
        setErrors(prev => ({
          ...prev,
          submit: error instanceof Error ? error.message : 'Failed to submit form',
        }));
      }
    }
  };

  return (
    <form role="form" onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="date" className="block text-sm font-medium text-gray-700">
          Birth Date
        </label>
        <input
          type="date"
          id="date"
          value={formData.date}
          onChange={e => setFormData(prev => ({ ...prev, date: e.target.value }))}
          onBlur={() => handleFieldTouch('date')}
          className={`mt-1 block w-full rounded-md shadow-sm ${
            touched.date && errors.date ? 'border-red-300' : 'border-gray-300'
          }`}
          required
          max={format(new Date(), 'yyyy-MM-dd')}
          aria-invalid={touched.date && !!errors.date}
          aria-describedby={touched.date && errors.date ? "date-error" : undefined}
        />
        {touched.date && errors.date && (
          <div id="date-error" role="alert" className="mt-1 text-sm text-red-600">{errors.date}</div>
        )}
      </div>

      <div>
        <label htmlFor="time" className="block text-sm font-medium text-gray-700">
          Birth Time
        </label>
        <input
          type="time"
          id="time"
          value={formData.time}
          onChange={e => {
            const newTime = e.target.value;
            setFormData(prev => ({ ...prev, time: newTime }));
            handleFieldTouch('time');
          }}
          onBlur={() => handleFieldTouch('time')}
          className={`mt-1 block w-full rounded-md shadow-sm ${
            touched.time && errors.time ? 'border-red-300' : 'border-gray-300'
          }`}
          required
          aria-invalid={touched.time && !!errors.time}
          aria-describedby={touched.time && errors.time ? "time-error" : undefined}
        />
        {touched.time && errors.time && (
          <div id="time-error" role="alert" className="mt-1 text-sm text-red-600">{errors.time}</div>
        )}
        <div className="mt-1 text-xs text-gray-500">
          Enter time in 24-hour format (HH:MM)
        </div>
      </div>

      <div>
        <label htmlFor="birthPlace" className="block text-sm font-medium text-gray-700">
          Birth Place
        </label>
        <div className="relative mt-1">
          <input
            type="text"
            id="birthPlace"
            value={formData.birthPlace}
            onChange={e => setFormData(prev => ({ ...prev, birthPlace: e.target.value }))}
            onBlur={() => handleFieldTouch('birthPlace')}
            className={`block w-full rounded-md shadow-sm ${
              touched.birthPlace && errors.birthPlace ? 'border-red-300' : 'border-gray-300'
            } ${formData.latitude && formData.longitude ? 'pr-10' : ''}`}
            required
            placeholder="e.g. London, UK"
            autoComplete="off"
            aria-invalid={touched.birthPlace && !!errors.birthPlace}
            aria-describedby={touched.birthPlace && errors.birthPlace ? "birthPlace-error" : undefined}
          />
          <div className="absolute inset-y-0 right-0 flex items-center pr-3">
            {isGeocoding && (
              <svg className="animate-spin h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {!isGeocoding && locationVerified && (
              <svg className="h-5 w-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
              </svg>
            )}
          </div>
        </div>
        {touched.birthPlace && errors.birthPlace && (
          <div id="birthPlace-error" role="alert" className="mt-1 text-sm text-red-600">{errors.birthPlace}</div>
        )}
        {locationVerified && formData.latitude && formData.longitude && (
          <div className="mt-2 text-sm text-gray-700">
            <div className="font-medium text-green-600">Location verified</div>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div>
                <span className="text-gray-500">Latitude:</span> {formData.latitude.toFixed(4)}
              </div>
              <div>
                <span className="text-gray-500">Longitude:</span> {formData.longitude.toFixed(4)}
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">Timezone:</span> {formData.timezone}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Submit error display */}
      {errors.submit && (
        <div className="rounded-md bg-red-50 p-4 mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Submission Error</h3>
              <div className="mt-2 text-sm text-red-700">
                {errors.submit}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading || isGeocoding}
          className={`px-4 py-2 rounded-md text-white ${
            isLoading || isGeocoding
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isLoading ? 'Processing...' : isGeocoding ? 'Finding location...' : 'Next'}
        </button>
      </div>
    </form>
  );
};

export default BirthDetailsForm;
