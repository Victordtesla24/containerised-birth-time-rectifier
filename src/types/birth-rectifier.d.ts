// Birth rectifier specialized type definitions

// Chart data interface
export interface ChartData {
  ascendant?: number;
  houses: Record<number, number>;
  planets: Record<string, {
    longitude: number;
    latitude?: number;
    house?: number;
    sign?: number;
    retrograde?: boolean;
  }>;
  confidence?: number;
}

// Questionnaire related types
export interface QuestionnaireAnswer {
  questionId: string;
  answer: string | string[] | Date | boolean | number;
  confidence?: number;
}

export interface QuestionnaireResponse {
  answers: QuestionnaireAnswer[];
  completedAt: Date;
}

// Analysis results
export interface RectificationResult {
  rectifiedBirthTime: string;
  confidence: number;
  chart: ChartData;
  analysisText?: string;
  planetaryPositions?: Array<{
    planet: string;
    sign: string;
    house: number;
    degree: number;
  }>;
}

// Ensure global process types
declare global {
  interface Window {
    // Add any window-specific properties here
  }

  namespace NodeJS {
    interface ProcessEnv {
      NODE_ENV: 'development' | 'production' | 'test';
      NEXT_PUBLIC_API_URL?: string;
    }
  }
}
