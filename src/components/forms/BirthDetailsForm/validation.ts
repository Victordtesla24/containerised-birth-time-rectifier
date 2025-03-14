import { FormState, ValidationErrors } from './types';
import { isValid, parse, isFuture, isAfter, subYears } from 'date-fns';
import { timezones } from './timezones';

/**
 * Validate birth details form data
 * @param data Form data to validate
 * @returns Validation errors if any
 */
export const validateBirthDetails = (data: FormState): ValidationErrors => {
  const errors: ValidationErrors = {};

  // Validate birth date
  if (!data.date) {
    errors.date = 'Birth date is required';
  } else {
    const parsedDate = parse(data.date, 'yyyy-MM-dd', new Date());
    if (!isValid(parsedDate)) {
      errors.date = 'Invalid date format';
    } else if (parsedDate > new Date()) {
      errors.date = 'Birth date cannot be in the future';
    }
  }

  // Validate birth time
  if (!data.time) {
    errors.time = 'Birth time is required';
  } else if (!/^([0-1]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$/.test(data.time) &&
            !/^([0-1]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?\s*(AM|PM|am|pm)$/.test(data.time)) {
    errors.time = 'Invalid time format. Please use HH:MM or HH:MM AM/PM format';
  }

  // Validate birth place
  if (!data.birthPlace) {
    errors.birthPlace = 'Birth place is required';
  } else if (data.birthPlace.length < 3) {
    errors.birthPlace = 'Please enter a more specific location';
  } else if (!/^[a-zA-Z\s,]+$/.test(data.birthPlace)) {
    errors.birthPlace = 'Birth place should only contain letters, spaces, and commas';
  }

  return errors;
};

/**
 * Check if validation errors object has any errors
 * @param errors Validation errors object
 * @returns Boolean indicating if there are any errors
 */
export const hasErrors = (errors: ValidationErrors): boolean => {
  return Object.keys(errors).length > 0;
};
