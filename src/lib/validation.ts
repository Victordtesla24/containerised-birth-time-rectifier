/**
 * Validation utilities for birth details and other form data
 */

// Birth details interface
interface BirthDetails {
  birthDate?: string;
  birthTime?: string;
  latitude?: string | number;
  longitude?: string | number;
  location?: string;
  fullName?: string;
  gender?: string;
}

// Validation result interface
interface ValidationResult {
  isValid: boolean;
  message?: string;
}

/**
 * Validate birth date format (YYYY-MM-DD)
 */
export function validateBirthDate(date: string): ValidationResult {
  if (!date) {
    return { isValid: false, message: 'Birth date is required' };
  }

  // Check format using regex (YYYY-MM-DD)
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(date)) {
    return { isValid: false, message: 'Birth date must be in YYYY-MM-DD format' };
  }

  // Check if date is valid
  const parsedDate = new Date(date);
  if (isNaN(parsedDate.getTime())) {
    return { isValid: false, message: 'Invalid birth date' };
  }

  // Check if date is in the past
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (parsedDate > today) {
    return { isValid: false, message: 'Birth date cannot be in the future' };
  }

  return { isValid: true };
}

/**
 * Validate birth time format (HH:MM or HH:MM:SS)
 */
export function validateBirthTime(time: string): ValidationResult {
  if (!time) {
    return { isValid: false, message: 'Birth time is required' };
  }

  // Check format using regex (HH:MM or HH:MM:SS)
  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/;
  if (!timeRegex.test(time)) {
    return { isValid: false, message: 'Birth time must be in HH:MM or HH:MM:SS format (24-hour)' };
  }

  return { isValid: true };
}

/**
 * Validate latitude (-90 to 90)
 */
export function validateLatitude(latitude: string | number): ValidationResult {
  if (latitude === undefined || latitude === null || latitude === '') {
    return { isValid: false, message: 'Latitude is required' };
  }

  const lat = typeof latitude === 'string' ? parseFloat(latitude) : latitude;

  if (isNaN(lat)) {
    return { isValid: false, message: 'Latitude must be a number' };
  }

  if (lat < -90 || lat > 90) {
    return { isValid: false, message: 'Latitude must be between -90 and 90' };
  }

  return { isValid: true };
}

/**
 * Validate longitude (-180 to 180)
 */
export function validateLongitude(longitude: string | number): ValidationResult {
  if (longitude === undefined || longitude === null || longitude === '') {
    return { isValid: false, message: 'Longitude is required' };
  }

  const lng = typeof longitude === 'string' ? parseFloat(longitude) : longitude;

  if (isNaN(lng)) {
    return { isValid: false, message: 'Longitude must be a number' };
  }

  if (lng < -180 || lng > 180) {
    return { isValid: false, message: 'Longitude must be between -180 and 180' };
  }

  return { isValid: true };
}

/**
 * Validate location
 */
export function validateLocation(location: string): ValidationResult {
  if (!location) {
    return { isValid: false, message: 'Location is required' };
  }

  if (location.trim().length < 2) {
    return { isValid: false, message: 'Location must be at least 2 characters' };
  }

  return { isValid: true };
}

/**
 * Validate all birth details
 */
export function validateBirthDetails(details: BirthDetails): ValidationResult {
  // Check required fields
  if (!details) {
    return { isValid: false, message: 'Birth details are required' };
  }

  // Validate birth date
  if (details.birthDate) {
    const dateResult = validateBirthDate(details.birthDate);
    if (!dateResult.isValid) {
      return dateResult;
    }
  } else {
    return { isValid: false, message: 'Birth date is required' };
  }

  // Validate birth time
  if (details.birthTime) {
    const timeResult = validateBirthTime(details.birthTime);
    if (!timeResult.isValid) {
      return timeResult;
    }
  } else {
    return { isValid: false, message: 'Birth time is required' };
  }

  // Validate latitude if provided
  if (details.latitude !== undefined) {
    const latResult = validateLatitude(details.latitude);
    if (!latResult.isValid) {
      return latResult;
    }
  }

  // Validate longitude if provided
  if (details.longitude !== undefined) {
    const lngResult = validateLongitude(details.longitude);
    if (!lngResult.isValid) {
      return lngResult;
    }
  }

  // Validate location if provided
  if (details.location) {
    const locationResult = validateLocation(details.location);
    if (!locationResult.isValid) {
      return locationResult;
    }
  }

  return { isValid: true };
}
