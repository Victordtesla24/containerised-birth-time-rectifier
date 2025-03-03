// Birth Details
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

// Questionnaire Response
export interface QuestionnaireResponse {
  lifeEvents: LifeEvent[];
  healthEvents?: HealthEvent[];
  relationships?: Relationship[];
  careerChanges?: CareerChange[];
}

export interface LifeEvent {
  type: string;
  date: string; // ISO format date
  description: string;
  impact: 'low' | 'medium' | 'high';
}

export interface HealthEvent {
  type: string;
  date: string; // ISO format date
  description: string;
  duration: string;
}

export interface Relationship {
  type: 'romantic' | 'friendship' | 'family' | 'professional';
  startDate: string; // ISO format date
  endDate?: string; // ISO format date
  description: string;
}

export interface CareerChange {
  type: 'job' | 'promotion' | 'education' | 'business';
  date: string; // ISO format date
  description: string;
}

// Chart Data
export interface ChartData {
  ascendant: number;
  planets: PlanetPosition[];
  houses: HouseData[];
  divisionalCharts?: Record<string, ChartData>;
}

export interface PlanetPosition {
  id: string;
  name: string;
  longitude: number;
  latitude: number;
  speed: number;
  house: number;
  explanation?: string;
}

export interface HouseData {
  number: number;
  startDegree: number;
  endDegree: number;
  planets: string[];
}

// Rectification Results
export interface RectificationResult {
  suggestedTime: string;
  confidence: number;
  reliability?: string;
  charts?: ChartData;
  taskPredictions?: Record<string, number>;
  explanation?: string;
  significantEvents?: SignificantEvent[];
}

export interface SignificantEvent {
  type: string;
  date: string;
  planetaryInfluence: string[];
  description: string;
}

// AI Model Types
export interface ModelPrediction {
  rectifiedTime: Date;
  confidence: number;
  explanation: string;
} 