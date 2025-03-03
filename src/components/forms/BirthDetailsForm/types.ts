import { BirthDetails } from '@/types';

export interface TimeZone {
  value: string;
  label: string;
}

export interface BirthDetailsFormProps {
  onSubmit: (data: BirthDetails) => Promise<void>;
  onValidation: (isValid: boolean) => void;
  initialData?: Partial<BirthDetails>;
  isLoading?: boolean;
}

export interface FormState {
  date: string;
  time: string;
  birthPlace: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
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
