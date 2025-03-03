// export type { BirthDetails, RectificationResult };

export interface PlanetPosition {
  planet: string;
  sign: string;
  degree: string;
  house: number;
  name?: string;
  longitude?: number;
  latitude?: number;
  speed?: number;
  retrograde?: boolean;
  explanation?: string;
  description?: string;
}

export interface HouseData {
  number: number;
  startDegree: number;
  endDegree: number;
  planets: PlanetPosition[];
}

export interface HouseDetails extends HouseData {
  sign: string;
  degree: number;
  description?: string;
}

export interface Aspect {
  planet1: string;
  planet2: string;
  aspectType: string;
  orb: number;
  influence: 'positive' | 'negative' | 'neutral';
  description?: string;
}

export interface ChartData {
  ascendant: number | {
    sign: string;
    degree: number;
    description?: string;
  };
  planets: PlanetPosition[];
  houses: HouseData[] | HouseDetails[];
  divisionalCharts: Record<string, ChartData>;
  aspects: Aspect[];
  visualization?: VisualizationData;
}

export interface VisualizationData {
  celestialLayers: CelestialLayer[];
  cameraPosition: Vector3D;
  lightingSetup: LightingSetup;
}

export interface CelestialLayer {
  depth: number;
  content: 'stars' | 'nebulae' | 'galaxies';
  parallaxFactor: number;
  position: Vector3D;
}

export interface Vector3D {
  x: number;
  y: number;
  z: number;
}

export interface LightingSetup {
  ambient: {
    color: string;
    intensity: number;
  };
  directional: {
    color: string;
    intensity: number;
    position: Vector3D;
  }[];
}

/**
 * Common type definitions for the Birth Time Rectifier application
 */

// Birth details provided by the user
export interface BirthDetails {
  name: string;
  gender: string;
  birthDate: string;
  approximateTime: string;
  birthLocation: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  timezone?: string;
}

// A single question from the questionnaire
export interface DynamicQuestion {
  id: string;
  text: string;
  type: 'yes_no' | 'multiple_choice' | 'date' | 'text';
  options?: (string | QuestionOption)[];
  weight: number;
}

// A single answer from the questionnaire
export interface QuestionAnswer {
  questionId: string;
  question: string;
  answer: string;
}

// The complete questionnaire response
export interface QuestionnaireResponse {
  birthDetails?: BirthDetails;
  answers: QuestionAnswer[];
  confidenceScore: number;
  sessionId?: string;
}

// A single significant life event
export interface SignificantEvent {
  date: string;
  description: string;
  confidence: number;
  impactAreas: string[];
}

// The result of birth time rectification
export interface RectificationResult {
  birthDetails: BirthDetails;
  originalTime: string;
  suggestedTime: string;
  confidence: number;
  reliability: string;
  taskPredictions: {
    time: number;
    ascendant: number;
    houses: number;
  };
  explanation: string;
  planetaryPositions: PlanetPosition[];
  significantEvents?: {
    past: SignificantEvent[];
    future: SignificantEvent[];
  };
}

// Questionnaire component props
export interface LifeEventsQuestionnaireProps {
  birthDetails?: BirthDetails;
  onSubmit: (data: QuestionnaireResponse) => Promise<void>;
  onProgress?: (progress: number) => void;
  isLoading?: boolean;
  initialData?: any;
}

// API error response
export interface ApiError {
  status: number;
  message: string;
  detail?: string | string[];
}

// Questionnaire generation request
export interface QuestionnaireGenerationRequest {
  birthDetails: BirthDetails;
  previousAnswers?: Record<string, string>;
  currentConfidence?: number;
  focusAreas?: string[];
  maxQuestions?: number;
}

// Questionnaire generation response
export interface QuestionnaireGenerationResponse {
  questions: DynamicQuestion[];
  confidence: number;
  sessionId?: string;
  message?: string;
}

// Life event prediction for astrological analysis
export interface LifeEventPrediction {
  date: string;
  description: string;
  confidence: number;
  impactAreas: string[];
  planetaryInfluences: string[];
  type: 'career' | 'relationship' | 'health' | 'spiritual' | 'education' | 'travel' | 'other';
  intensity: 'low' | 'medium' | 'high';
  timeframe: 'past' | 'present' | 'future';
}

export interface QuestionOption {
  id: string;
  text: string;
}
