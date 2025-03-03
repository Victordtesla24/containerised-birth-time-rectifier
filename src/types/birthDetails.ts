export interface BirthDetails {
  date: Date;
  time: string;
  birthPlace: string;
  latitude: number;
  longitude: number;
  timezone: string;
  additionalFactors?: {
    majorLifeEvents?: string[];
    healthHistory?: string[];
  };
}

export interface RectificationResult {
  suggestedTime: string;
  confidence: number;
  reliability: string;
} 