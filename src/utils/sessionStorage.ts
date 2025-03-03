/**
 * sessionStorage.ts
 * Utility for managing session storage data consistently across the application
 */

import { BirthDetails, QuestionnaireResponse } from '@/types';

// Define interfaces for our stored data
export interface QuestionnaireSession {
  sessionId: string;
  questionHistory: any[];
  userResponses: Record<string, any>;
  confidence: number;
}

export interface AnalysisResults {
  rectifiedBirthTime: string;
  confidenceScore: number;
  chartData: any;
  interpretations: any[];
}

// Session storage keys
const KEYS = {
  BIRTH_DETAILS: 'birthTimeRectifier_birthDetails',
  QUESTIONNAIRE: 'birthTimeRectifier_questionnaire',
  ANALYSIS: 'birthTimeRectifier_analysis',
};

// Birth details functions
export const getBirthDetails = (): BirthDetails | undefined => {
  if (typeof window !== 'undefined') {
    const data = window.sessionStorage.getItem(KEYS.BIRTH_DETAILS);
    return data ? JSON.parse(data) : undefined;
  }
  return undefined;
};

export const saveBirthDetails = (data: BirthDetails): void => {
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(KEYS.BIRTH_DETAILS, JSON.stringify(data));
  }
};

// Questionnaire functions
export const saveQuestionnaireData = (data: QuestionnaireResponse): void => {
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(KEYS.QUESTIONNAIRE, JSON.stringify(data));
  }
};

export const getQuestionnaireData = (): QuestionnaireResponse | null => {
  if (typeof window !== 'undefined') {
    const data = window.sessionStorage.getItem(KEYS.QUESTIONNAIRE);
    return data ? JSON.parse(data) : null;
  }
  return null;
};

// Analysis results
export const saveAnalysisResults = (data: AnalysisResults): void => {
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(KEYS.ANALYSIS, JSON.stringify(data));
  }
};

export const getAnalysisResults = (): AnalysisResults | null => {
  if (typeof window !== 'undefined') {
    const data = window.sessionStorage.getItem(KEYS.ANALYSIS);
    return data ? JSON.parse(data) : null;
  }
  return null;
};

// Rectification results (aliases for analysis results)
export const getRectificationResult = getAnalysisResults;
export const saveRectificationResult = saveAnalysisResults;

// Clear all data
export const clearAllData = (): void => {
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(KEYS.BIRTH_DETAILS);
    window.sessionStorage.removeItem(KEYS.QUESTIONNAIRE);
    window.sessionStorage.removeItem(KEYS.ANALYSIS);
  }
};
