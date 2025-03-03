import { FormState, ValidationErrors } from './types';
import { isValid, parse, isFuture, isAfter, subYears } from 'date-fns';
import { timezones } from './timezones';

export function validateBirthDetails(data: FormState): ValidationErrors {
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
  } else {
    // HTML5 time input format: HH:mm
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$/;
    if (!timeRegex.test(data.time)) {
      errors.time = 'Invalid time format';
    } else {
      const [hours, minutes] = data.time.split(':').map(Number);
      if (hours >= 24 || minutes >= 60) {
        errors.time = 'Invalid time format';
      }
    }
  }

  // Validate birth place
  if (!data.birthPlace) {
    errors.birthPlace = 'Birth place is required';
  } else if (data.birthPlace.length < 3) {
    errors.birthPlace = 'Birth place must be at least 3 characters long';
  } else if (!/^[a-zA-Z\s,]+$/.test(data.birthPlace)) {
    errors.birthPlace = 'Birth place should only contain letters, spaces, and commas';
  }

  return errors;
};

export function hasErrors(errors: ValidationErrors): boolean {
  return Object.keys(errors).length > 0;
}
