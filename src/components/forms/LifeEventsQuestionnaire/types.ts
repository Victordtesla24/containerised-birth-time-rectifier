import { BirthDetails, QuestionnaireResponse, QuestionOption } from '@/types';

/**
 * Props for the LifeEventsQuestionnaire component
 */
export interface LifeEventsQuestionnaireProps {
  /**
   * Optional birth details for context-aware questioning
   */
  birthDetails: BirthDetails;

  /**
   * Callback function when questionnaire is submitted
   * @param data The questionnaire response data
   */
  onSubmit?: (data: QuestionnaireSubmitData) => void;

  /**
   * Optional callback function to report questionnaire progress
   * @param data The questionnaire progress data
   */
  onProgress?: (data: QuestionnaireProgressData) => void;

  /**
   * Flag to indicate if questionnaire is in a loading state
   */
  isLoading?: boolean;

  /**
   * Optional initial data to pre-populate questionnaire
   */
  initialData?: QuestionnaireResponse;
}

/**
 * Question response data
 */
export interface QuestionResponse {
  /**
   * Unique identifier for the question
   */
  id: string;

  /**
   * The question text
   */
  text: string;

  /**
   * The question options
   */
  options: QuestionOption[];
}

export interface QuestionnaireSubmitData {
  answers: Record<string, string>;
  confidence: number;
  questionIds: string[];
}

export interface QuestionnaireProgressData {
  answeredQuestions: number;
  totalQuestions: number;
  confidence: number;
}

export interface QuestionState {
  id: string;
  answer: string | null;
}
