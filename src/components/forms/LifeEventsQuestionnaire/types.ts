import { BirthDetails, QuestionnaireResponse } from '@/types';

/**
 * Props for the LifeEventsQuestionnaire component
 */
export interface LifeEventsQuestionnaireProps {
  /**
   * Optional birth details for context-aware questioning
   */
  birthDetails?: BirthDetails;
  
  /**
   * Callback function when questionnaire is submitted
   * @param data The questionnaire response data
   */
  onSubmit: (data: QuestionnaireResponse) => Promise<void>;
  
  /**
   * Optional callback function to report questionnaire progress
   * @param progress The current progress as a percentage
   */
  onProgress?: (progress: number) => void;
  
  /**
   * Flag to indicate if questionnaire is in a loading state
   */
  isLoading?: boolean;
  
  /**
   * Optional initial data to pre-populate questionnaire
   */
  initialData?: any;
}

/**
 * Question response data
 */
export interface QuestionResponse {
  /**
   * Unique identifier for the question
   */
  questionId: string;
  
  /**
   * The question text
   */
  question: string;
  
  /**
   * The user's answer
   */
  answer: string;
}

export interface QuestionState {
  currentStep: number;
  lifeEvents: {
    type: string;
    date: string;
    description: string;
    impact: 'low' | 'medium' | 'high';
  }[];
  healthEvents: {
    type: string;
    date: string;
    description: string;
    duration: string;
  }[];
  relationships: {
    type: 'romantic' | 'friendship' | 'family' | 'professional';
    startDate: string;
    endDate?: string;
    description: string;
  }[];
  careerChanges: {
    type: 'job' | 'promotion' | 'education' | 'business';
    date: string;
    description: string;
  }[];
} 