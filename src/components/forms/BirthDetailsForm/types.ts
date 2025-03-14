import { BirthDetails } from '@/types';

export interface LocationSuggestion {
  place_id: string;
  description: string;
}

export interface TimeZone {
  value: string;
  label: string;
}

export interface BirthDetailsFormProps {
  onSubmit: (birthDetails: BirthDetails) => Promise<{session_id: string} | void>;
  onValidation?: ValidationHandler;
  initialData?: Partial<BirthDetails>;
  isLoading?: boolean;
}

export interface FormState {
  date: string;
  time: string;
  birthPlace: string;
  latitude: number;
  longitude: number;
  timezone: string;
  // Life events questions will be added after initial analysis
  lifeEvents?: Record<string, boolean>;
}

export interface ValidationErrors {
  date?: string;
  time?: string;
  birthPlace?: string;
  submit?: string;
  lifeEvents?: Record<string, string>;
}

export interface LifeEventQuestion {
  id: string;
  question: string;
  category: 'career' | 'relationships' | 'health' | 'other';
}

export interface TimeRange {
  startTime: string;
  endTime: string;
}

export type ValidationHandler = (isValid: boolean, data?: any) => void;

export interface FormattedBirthDetails extends BirthDetails {
  time_accuracy: string;
  time_range: {
    start_time: string;
    end_time: string;
  } | null;
  location: {
    name: string;
    latitude: number;
    longitude: number;
  };
  email: string;
}
