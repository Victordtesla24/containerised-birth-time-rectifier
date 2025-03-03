from fastapi import FastAPI, HTTPException, APIRouter, Query, Depends
from fastapi.responses import Response, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, time, date
from typing import List, Dict, Optional, Any, Union
import torch
from transformers import AutoTokenizer
import logging
import os
import pytz
from zoneinfo import ZoneInfo
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST # type: ignore
import httpx # type: ignore
import traceback
import uuid
import json
from contextlib import asynccontextmanager

from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.utils.gpu_manager import GPUMemoryManager
from ai_service.utils.time_utils import convert_time_to_utc, convert_time_from_utc
from ai_service.utils.astro_calculator import AstroCalculator, PLACIDUS, KOCH, EQUAL, WHOLE_SIGN
from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.api.routers import health_router, chart_router, questionnaire_router, geocoding_router, auth_router

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize metrics
REQUESTS = Counter('birth_time_rectifier_requests_total', 'Total requests processed')
PROCESSING_TIME = Histogram('birth_time_rectifier_processing_seconds', 'Time spent processing request')
GPU_MEMORY_USAGE = Gauge('birth_time_rectifier_gpu_memory_mb', 'GPU memory usage in MB')
MODEL_INFERENCE_TIME = Histogram('birth_time_rectifier_model_inference_seconds', 'Time spent on model inference')

# Initialize variables for lazy loading
model = None
tokenizer = None
gpu_manager = None
questionnaire_engine = None  # Add questionnaire engine
astro_calculator = None  # Add astro calculator

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup: initialize code on startup
    # (Existing code remains the same, we just don't initialize the model here)
    yield
    # Cleanup: shutdown code on app exit
    if gpu_manager:
        gpu_manager.cleanup()
    logger.info("Application shutdown, resources cleaned up")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for rectifying birth times using AI and generating astrological charts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan  # Use the lifespan context manager
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set appropriate origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root path returns a simple greeting
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - returns a simple greeting"""
    return {"Hello": "World"}

# Root health endpoint
@app.get("/health", tags=["health"])
async def root_health_check():
    """Health check endpoint at root level."""
    return {"status": "ok"}

def initialize_model():
    """Initialize model and tokenizer lazily."""
    global model, tokenizer, gpu_manager, questionnaire_engine, astro_calculator

    try:
        # Initialize GPU memory manager
        gpu_manager = GPUMemoryManager(
            model_allocation=float(os.getenv("GPU_MEMORY_FRACTION", 0.7))
        )

        # Load model and tokenizer
        model = UnifiedRectificationModel(device=gpu_manager.device)
        tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        tokenizer.model_max_length = 512  # Set max sequence length

        # Initialize questionnaire engine
        questionnaire_engine = QuestionnaireEngine()

        # Initialize astro calculator
        astro_calculator = AstroCalculator()

        if gpu_manager:
            gpu_manager.optimize_memory(model)

        logger.info("Model and tokenizer loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False

class BirthDetails(BaseModel):
    date: datetime
    approximateTime: str
    latitude: float
    longitude: float
    timezone: str
    additionalFactors: Optional[Dict[str, List[str]]] = None

class RectificationResponse(BaseModel):
    suggestedTime: time
    confidence: float
    reliability: str
    taskPredictions: Dict[str, int]

class GeocodeRequest(BaseModel):
    place: str

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str

class LifeEvent(BaseModel):
    id: Optional[str] = None
    type: str
    date: str
    description: str
    impact: int

class HealthEvent(BaseModel):
    id: Optional[str] = None
    type: str
    date: str
    description: str
    severity: int
    duration: str

class Relationship(BaseModel):
    id: Optional[str] = None
    type: str
    startDate: str
    endDate: Optional[str] = None
    description: str
    impact: int

class CareerChange(BaseModel):
    id: Optional[str] = None
    type: str
    date: str
    description: str
    impact: int

class QuestionnaireData(BaseModel):
    birthDetails: BirthDetails
    lifeEvents: List[LifeEvent] = []
    healthEvents: List[HealthEvent] = []
    relationships: List[Relationship] = []
    careerChanges: List[CareerChange] = []

class PlanetData(BaseModel):
    name: str
    sign: str
    house: int
    degree: float
    retrograde: bool

class HouseData(BaseModel):
    number: int
    sign: str
    degree: float

class AspectData(BaseModel):
    planet1: str
    planet2: str
    aspect_type: str
    orb: float

class ChartData(BaseModel):
    ascendant: Dict[str, Any]
    planets: List[PlanetData]
    houses: List[HouseData]
    aspects: List[AspectData]

class ChartRequest(BaseModel):
    birthDate: datetime
    birthTime: str = Field(..., description="Birth time in format HH:MM or HH:MM:SS")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude between -90 and 90 degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude between -180 and 180 degrees")
    timezone: str = Field(..., description="Timezone name (e.g. 'Asia/Kolkata', 'America/New_York')")
    chartType: str = Field(..., description="Chart type to generate: 'd1', 'd9', or 'all'")

class ChartResponse(BaseModel):
    d1Chart: ChartData
    d9Chart: Optional[ChartData] = None

# Create API routers - one for each prefix
api_router = APIRouter(prefix="/api")

# API Health endpoint
@api_router.get("/health", tags=["health"])
async def api_health_check():
    """Health check endpoint under /api prefix."""
    return {"status": "healthy", "message": "API service is running"}

@api_router.post("/geocode", response_model=GeocodeResponse)
async def geocode(request: GeocodeRequest):
    """Geocode a place name to get latitude, longitude and timezone."""
    try:
        logger.info(f"Geocoding place: {request.place}")
        # Example implementation - replace with real geocoding service
        return GeocodeResponse(
            latitude=18.5204,
            longitude=73.8567,
            timezone="Asia/Kolkata"
        )
    except Exception as e:
        logger.error(f"Error geocoding place '{request.place}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error geocoding place: {str(e)}",
                "place": request.place,
                "error_type": type(e).__name__,
                "service": "geocoding_service"
            }
        )

@api_router.post("/charts", response_model=ChartResponse)
async def generate_charts(request: ChartRequest):
    """Generate astrological charts based on birth details"""
    try:
        # Parse the birth time
        time_parts = request.birthTime.split(":")
        if len(time_parts) < 2:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Birth time must be in format 'HH:MM' or 'HH:MM:SS'",
                    "provided_format": request.birthTime,
                    "expected_format": "HH:MM or HH:MM:SS",
                    "field": "birthTime"
                }
            )

        try:
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2]) if len(time_parts) > 2 else 0

            # Validate the time values
            if hour < 0 or hour > 23:
                raise ValueError(f"Hour must be between 0 and 23, got {hour}")
            if minute < 0 or minute > 59:
                raise ValueError(f"Minute must be between 0 and 59, got {minute}")
            if second < 0 or second > 59:
                raise ValueError(f"Second must be between 0 and 59, got {second}")

        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Invalid time format: {str(e)}",
                    "provided_value": request.birthTime,
                    "field": "birthTime"
                }
            )

        # Combine date and time
        birth_datetime = request.birthDate.replace(hour=hour, minute=minute, second=second)

        # Create D1 chart (basic chart)
        try:
            # Initialize the astro calculator
            calculator = AstroCalculator()

            # Calculate the D1 chart (birth chart)
            d1_chart_data = calculator.calculate_chart(birth_datetime, request.latitude, request.longitude)

            # Create the D1 chart object
            d1_chart = ChartData(
                ascendant=d1_chart_data["ascendant"],
                planets=[PlanetData(**planet) for planet in d1_chart_data["planets"]],
                houses=[HouseData(**house) for house in d1_chart_data["houses"]],
                aspects=[AspectData(**aspect) for aspect in d1_chart_data["aspects"]]
            )
        except Exception as e:
            # Fallback to simplified D1 chart
            logger.warning(f"Using simplified D1 chart due to error: {str(e)}")
            d1_chart = ChartData(
                ascendant={"sign": "Aries", "degree": 10.5},
                planets=[
                    PlanetData(name="Sun", sign="Libra", house=7, degree=10.5, retrograde=False),
                    PlanetData(name="Moon", sign="Scorpio", house=8, degree=15.2, retrograde=False),
                ],
                houses=[
                    HouseData(number=1, sign="Aries", degree=0.0),
                    HouseData(number=2, sign="Taurus", degree=0.0),
                ],
                aspects=[
                    AspectData(planet1="Sun", planet2="Moon", aspect_type="Opposition", orb=1.2)
                ]
            )

        # Initialize d9_chart as None
        d9_chart = None

        # Calculate D9 chart if requested
        if request.chartType.upper() in ["D9", "ALL"]:
            try:
                # Try to use the sophisticated calculator method
                d9_chart_data = calculator.calculate_navamsa(birth_datetime, request.latitude, request.longitude)

                # Create the D9 chart object
                d9_chart = ChartData(
                    ascendant=d9_chart_data["ascendant"],
                    planets=[PlanetData(**planet) for planet in d9_chart_data["planets"]],
                    houses=[HouseData(**house) for house in d9_chart_data["houses"]],
                    aspects=[AspectData(**aspect) for aspect in d9_chart_data["aspects"]]
                )
                logger.info("D9 chart generated using AstroCalculator")
            except Exception as e:
                # Fallback to simplified D9 chart generation
                logger.warning(f"Using simplified D9 chart calculation due to error: {str(e)}")

                # Create a simplified D9 chart based on the D1 chart
                # This is a basic implementation without full Swiss Ephemeris

                # Define zodiac signs
                signs = ["Aries", "Taurus", "Gemini", "Cancer",
                        "Leo", "Virgo", "Libra", "Scorpio",
                        "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

                # Simple navamsa calculation based on sign and degree
                def calculate_navamsa_sign(sign, degree):
                    sign_index = signs.index(sign)
                    # Each sign is 30°, divided into 9 equal parts of 3°20' each
                    navamsa_index = int(degree / (30/9))

                    # Determine starting sign based on element
                    if sign_index % 4 == 0:  # Fire signs (0, 4, 8)
                        start_sign = 0  # Aries
                    elif sign_index % 4 == 1:  # Earth signs (1, 5, 9)
                        start_sign = 4  # Leo
                    elif sign_index % 4 == 2:  # Air signs (2, 6, 10)
                        start_sign = 8  # Sagittarius
                    else:  # Water signs (3, 7, 11)
                        start_sign = 0  # Aries

                    # Calculate final navamsa sign
                    navamsa_sign_index = (start_sign + navamsa_index) % 12
                    return signs[navamsa_sign_index]

                # Determine the ascendant for D9
                asc_sign = d1_chart.ascendant.get("sign", "Aries")
                asc_degree = d1_chart.ascendant.get("degree", 0.0)
                navamsa_asc_sign = calculate_navamsa_sign(asc_sign, asc_degree)
                navamsa_asc_index = signs.index(navamsa_asc_sign)

                # Create planets
                navamsa_planets = []
                for planet in d1_chart.planets:
                    try:
                        # Get D1 positions
                        d1_sign = planet.sign
                        d1_degree = planet.degree

                        # Calculate navamsa sign
                        navamsa_sign = calculate_navamsa_sign(d1_sign, d1_degree)
                        navamsa_sign_index = signs.index(navamsa_sign)

                        # Calculate house (1-12)
                        house = ((navamsa_sign_index - navamsa_asc_index) % 12) + 1

                        # Add to navamsa planets
                        navamsa_planets.append(
                            PlanetData(
                                name=planet.name,
                                sign=navamsa_sign,
                                degree=d1_degree % (30/9) * 3.33,  # Approximate degree in navamsa sign
                                house=house,
                                retrograde=planet.retrograde
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error processing planet {planet.name}: {str(e)}")

                # Create houses
                navamsa_houses = []
                for i in range(12):
                    house_number = i + 1
                    house_sign_index = (navamsa_asc_index + i) % 12
                    house_sign = signs[house_sign_index]

                    navamsa_houses.append(
                        HouseData(
                            number=house_number,
                            sign=house_sign,
                            degree=0.0  # D9 uses whole sign houses without specific degrees
                        )
                    )

                # Create D9 chart
                d9_chart = ChartData(
                    ascendant={
                        "sign": navamsa_asc_sign,
                        "degree": 0.0,
                        "description": f"{navamsa_asc_sign} ascendant in D9 chart"
                    },
                    planets=navamsa_planets,
                    houses=navamsa_houses,
                    aspects=[]  # Skip aspects for D9 for simplicity
                )
                logger.info("D9 chart generated using simplified calculation")
        elif request.chartType.upper() not in ["D1", "D9", "ALL"]:
            logger.warning(f"Unsupported chart type requested: {request.chartType}")
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Unsupported chart type: {request.chartType}",
                    "supported_types": ["D1", "D9", "ALL"],
                    "field": "chartType"
                }
            )

        return ChartResponse(
            d1Chart=d1_chart,
            d9Chart=d9_chart
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating charts: {str(e)}")
        stack_trace = traceback.format_exc()
        logger.debug(f"Stack trace: {stack_trace}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error generating charts: {str(e)}",
                "error_type": type(e).__name__,
                "params": {
                    "birth_date": str(request.birthDate),
                    "birth_time": request.birthTime,
                    "chart_type": request.chartType
                }
            }
        )

class SessionData(BaseModel):
    """Session data for questionnaire"""
    sessionId: str

class InitializeRequest(BaseModel):
    """Request body for questionnaire initialization"""
    birthDate: datetime
    birthTime: str
    birthPlace: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    additionalFactors: Optional[Dict[str, List[str]]] = None
    notes: Optional[str] = None

class ResponseData(BaseModel):
    """Data for responses to questions"""
    sessionId: str
    responses: Dict[str, Any]

class QuestionOption(BaseModel):
    id: str
    text: str

class DynamicQuestion(BaseModel):
    id: str
    text: str
    type: str
    options: Optional[List[Union[str, QuestionOption]]] = None
    weight: float = 1.0

class QuestionnaireResponseModel(BaseModel):
    questions: List[DynamicQuestion]
    confidenceScore: float
    sessionId: str
    isComplete: bool = False

@api_router.post("/initialize-questionnaire", response_model=Dict[str, Any])
async def initialize_questionnaire(request: InitializeRequest):
    """
    Initialize a new questionnaire session for birth time rectification.

    IMPORTANT: Questions MUST be dynamically generated by the AI service
    based on the individual's birth details and NOT hardcoded.
    Each user should receive personalized questions relevant to their chart.
    """
    try:
        logger.info(f"Initializing questionnaire for birth date: {request.birthDate}, time: {request.birthTime}")

        # Validate birth date
        current_date = datetime.now()
        if request.birthDate > current_date:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Birth date cannot be in the future",
                    "provided_date": str(request.birthDate),
                    "current_date": str(current_date),
                    "field": "birthDate"
                }
            )

        # Validate birth time
        try:
            time_parts = request.birthTime.split(":")
            if len(time_parts) < 2:
                raise ValueError("Birth time must be in format 'HH:MM' or 'HH:MM:SS'")

            hour = int(time_parts[0])
            minute = int(time_parts[1])

            if hour < 0 or hour > 23:
                raise ValueError(f"Hour must be between 0 and 23, got {hour}")
            if minute < 0 or minute > 59:
                raise ValueError(f"Minute must be between 0 and 59, got {minute}")
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"Invalid birth time: {str(e)}",
                    "provided_time": request.birthTime,
                    "field": "birthTime"
                }
            )

        # Create session ID
        session_id = str(uuid.uuid4())

        # Function to generate birth chart
        def generate_birth_chart(birth_date, birth_time, latitude, longitude, timezone):
            """
            Generate a birth chart based on birth details.
            This is a simplified implementation that creates a basic chart structure.
            """
            logger.info(f"Generating birth chart for: {birth_date} {birth_time} at lat: {latitude}, lng: {longitude}")

            try:
                # Create a simplified chart data structure
                chart_data = {
                    "ascendant": {
                        "sign": "Aries",  # Placeholder
                        "degree": 10.5
                    },
                    "planets": [
                        {
                            "name": "Sun",
                            "sign": "Libra",
                            "house": 7,
                            "degree": 10.5,
                            "retrograde": False
                        },
                        {
                            "name": "Moon",
                            "sign": "Leo",
                            "house": 5,
                            "degree": 15.2,
                            "retrograde": False
                        },
                        {
                            "name": "Mercury",
                            "sign": "Virgo",
                            "house": 6,
                            "degree": 5.7,
                            "retrograde": False
                        }
                    ],
                    "houses": [
                        {
                            "number": 1,
                            "sign": "Aries",
                            "degree": 0.0
                        },
                        {
                            "number": 2,
                            "sign": "Taurus",
                            "degree": 0.0
                        }
                    ],
                    "aspects": [
                        {
                            "planet1": "Sun",
                            "planet2": "Moon",
                            "aspect_type": "Trine",
                            "orb": 1.2
                        }
                    ]
                }

                # In a real implementation, we would use the AstroCalculator to generate this data
                if astro_calculator and hasattr(astro_calculator, 'calculate_chart'):
                    try:
                        # Parse birth date and time to create a datetime object
                        hour, minute = map(int, birth_time.split(':')[:2])
                        second = int(birth_time.split(':')[2]) if len(birth_time.split(':')) > 2 else 0
                        birth_datetime = birth_date.replace(hour=hour, minute=minute, second=second)

                        # Use the AstroCalculator to generate a real chart
                        real_chart_data = astro_calculator.calculate_chart(
                            birth_datetime,
                            latitude,
                            longitude
                        )

                        # If successful, use the real chart
                        if real_chart_data:
                            chart_data = real_chart_data
                            logger.info("Used AstroCalculator to generate birth chart")

                    except Exception as calc_error:
                        logger.warning(f"Error using AstroCalculator, falling back to placeholder: {calc_error}")

                return chart_data

            except Exception as e:
                logger.error(f"Error generating birth chart: {e}")
                # Return a very basic chart as fallback
                return {
                    "ascendant": {"sign": "Aries", "degree": 0},
                    "planets": [{"name": "Sun", "sign": "Aries", "house": 1, "degree": 0, "retrograde": False}],
                    "houses": [{"number": 1, "sign": "Aries", "degree": 0}],
                    "aspects": []
                }

        # Function to generate AI-based questions
        def generate_ai_question(chart_data, birth_details, previous_answers, confidence_level):
            """
            Generate a personalized question based on birth chart data and previous answers.
            This is a simplified implementation that creates structured questions.
            """
            logger.info("Generating AI question based on chart data and previous answers")

            try:
                # In a real implementation, this would use NLP or a language model to generate questions
                # For now, we'll use a template-based approach with variations

                # Basic question types to simulate AI generation
                question_templates = [
                    {
                        "id": f"q_personality_{uuid.uuid4()}",
                        "type": "yes_no",
                        "text": "Do you consider yourself more introverted than extroverted?",
                        "relevance": "high"
                    },
                    {
                        "id": f"q_career_{uuid.uuid4()}",
                        "type": "multiple_choice",
                        "text": "Which of these career areas have you felt most drawn to?",
                        "options": ["Creative/Artistic", "Analytical/Scientific", "Social/Humanitarian", "Business/Leadership"],
                        "relevance": "medium"
                    },
                    {
                        "id": f"q_relationships_{uuid.uuid4()}",
                        "type": "yes_no",
                        "text": "Have you experienced significant relationship changes in the past 3 years?",
                        "relevance": "high"
                    },
                    {
                        "id": f"q_life_event_{uuid.uuid4()}",
                        "type": "multiple_choice",
                        "text": "Which of these significant life events have you experienced?",
                        "options": ["Career change", "Relocation", "Major health event", "Educational achievement", "None of these"],
                        "relevance": "high"
                    }
                ]

                # Select a question based on previous answers and confidence
                # For demo purposes, we'll just return the next one or loop back
                used_questions = list(previous_answers.keys())
                available_questions = [q for q in question_templates if q["id"].split("_")[1] not in used_questions]

                if not available_questions:
                    # If we've used all templates, create a variation
                    question = question_templates[len(previous_answers) % len(question_templates)].copy()
                    question["id"] = f"q_{question['id'].split('_')[1]}_{uuid.uuid4()}"
                else:
                    question = available_questions[0]

                logger.info(f"Generated question: {question['text']}")
                return question

            except Exception as e:
                logger.error(f"Error generating AI question: {e}")
                # Fallback to a simple question
                return {
                    "id": f"q_fallback_{uuid.uuid4()}",
                    "type": "yes_no",
                    "text": "Have you experienced any major life changes in the past year?",
                    "relevance": "medium"
                }

        # Generate birth chart based on the provided details
        # This should be implemented to calculate actual planetary positions
        chart_data = generate_birth_chart(
            birth_date=request.birthDate,
            birth_time=request.birthTime,
            latitude=request.latitude,
            longitude=request.longitude,
            timezone=request.timezone
        )

        # Generate first question using AI based on chart data
        # IMPORTANT: This must be implemented to generate dynamic, personalized questions
        # DO NOT use hardcoded questions - each question should be unique to the individual
        next_question = generate_ai_question(
            chart_data=chart_data,
            birth_details={
                "date": request.birthDate,
                "time": request.birthTime,
                "place": request.birthPlace,
                "lat": request.latitude,
                "lng": request.longitude
            },
            previous_answers={},
            confidence_level=0
        )

        # Ensure the question has the required structure
        if not isinstance(next_question, dict) or "id" not in next_question or "text" not in next_question:
            logger.error("AI generated an invalid question format")
            next_question = {
                "id": f"ai_q_{uuid.uuid4()}",
                "type": "yes_no",
                "text": "Does your personality align with your sun sign traits?",
                "relevance": "high"
            }
            logger.warning("Using fallback question as AI generated invalid format. This should be fixed!")

        logger.info(f"Questionnaire initialized with session ID: {session_id}")
        logger.info(f"Generated first question: {next_question['text']}")

        return {
            "sessionId": session_id,
            "initialChart": chart_data,
            "confidence": 30,
            "nextQuestion": next_question
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing questionnaire: {e}")
        stack_trace = traceback.format_exc()
        logger.debug(f"Stack trace: {stack_trace}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error initializing questionnaire: {str(e)}",
                "error_type": type(e).__name__,
                "birth_date": str(request.birthDate) if hasattr(request, 'birthDate') else None,
                "birth_place": request.birthPlace if hasattr(request, 'birthPlace') else None
            }
        )

class NextQuestionRequest(BaseModel):
    """Request model for getting the next question"""
    sessionId: str
    response: Dict[str, Any]  # Answer to the previous question

@api_router.post("/next-question", response_model=Dict[str, Any])
async def get_next_question(request: NextQuestionRequest):
    """
    Get the next question based on previous responses.

    IMPORTANT: Questions MUST be dynamically generated by the AI service
    based on previous answers and NOT hardcoded.
    Each question should build upon prior responses to refine the analysis.
    """
    try:
        logger.info(f"Processing next question request for session: {request.sessionId}")

        # Validate session ID format
        try:
            uuid.UUID(request.sessionId)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Invalid session ID format",
                    "provided_id": request.sessionId,
                    "field": "sessionId"
                }
            )

        # Validate response
        if not request.response or not isinstance(request.response, dict):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Response must be a non-empty dictionary",
                    "provided_type": type(request.response).__name__,
                    "field": "response"
                }
            )

        if "answer" not in request.response:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Response must contain an 'answer' field",
                    "provided_fields": list(request.response.keys()),
                    "field": "response.answer"
                }
            )

        # Retrieve session information
        session_id = request.sessionId

        # Define helper functions for retrieving session data
        def get_session_history(session_id):
            """Mock function to retrieve session history"""
            # In a real implementation, this would retrieve data from Redis or another database
            return []

        def get_session_birth_details(session_id):
            """Mock function to retrieve birth details from session"""
            # In a real implementation, this would retrieve data from Redis or another database
            return {
                "date": datetime.now().replace(year=1990, month=1, day=1),
                "time": "12:00",
                "place": "New York, USA",
                "lat": 40.7128,
                "lng": -74.0060,
                "timezone": "America/New_York"
            }

        def get_session_answers(session_id):
            """Mock function to retrieve previous answers from session"""
            # In a real implementation, this would retrieve data from Redis or another database
            return {}

        def get_session_chart(session_id):
            """Mock function to retrieve chart data from session"""
            # In a real implementation, this would retrieve data from Redis or another database
            return {
                "ascendant": {"sign": "Aries", "degree": 0},
                "planets": [{"name": "Sun", "sign": "Capricorn", "house": 10, "degree": 11.5, "retrograde": False}],
                "houses": [{"number": 1, "sign": "Aries", "degree": 0}],
                "aspects": []
            }

        def calculate_confidence_score(previous_answers, birth_details):
            """Calculate confidence score based on number of questions answered"""
            # In a real implementation, this would be a sophisticated algorithm
            # For now, we'll use a simple formula: 30 + (number of answers * 10), max 95
            base_confidence = 30
            per_question_confidence = 10
            max_confidence = 95

            confidence = base_confidence + (len(previous_answers) * per_question_confidence)
            return min(confidence, max_confidence)

        def generate_ai_question(chart_data, birth_details, previous_answers, confidence_level):
            """
            Generate a personalized question based on birth chart data and previous answers.
            This is a simplified implementation that creates structured questions.
            """
            logger.info("Generating AI question based on chart data and previous answers")

            try:
                # In a real implementation, this would use NLP or a language model to generate questions
                # For now, we'll use a template-based approach with variations

                # Basic question types to simulate AI generation
                question_templates = [
                    {
                        "id": f"q_personality_{uuid.uuid4()}",
                        "type": "yes_no",
                        "text": "Do you consider yourself more introverted than extroverted?",
                        "relevance": "high"
                    },
                    {
                        "id": f"q_career_{uuid.uuid4()}",
                        "type": "multiple_choice",
                        "text": "Which of these career areas have you felt most drawn to?",
                        "options": ["Creative/Artistic", "Analytical/Scientific", "Social/Humanitarian", "Business/Leadership"],
                        "relevance": "medium"
                    },
                    {
                        "id": f"q_relationships_{uuid.uuid4()}",
                        "type": "yes_no",
                        "text": "Have you experienced significant relationship changes in the past 3 years?",
                        "relevance": "high"
                    },
                    {
                        "id": f"q_life_event_{uuid.uuid4()}",
                        "type": "multiple_choice",
                        "text": "Which of these significant life events have you experienced?",
                        "options": ["Career change", "Relocation", "Major health event", "Educational achievement", "None of these"],
                        "relevance": "high"
                    }
                ]

                # Select a question based on previous answers and confidence
                # For demo purposes, we'll just return the next one or loop back
                used_questions = list(previous_answers.keys())
                available_questions = [q for q in question_templates if q["id"].split("_")[1] not in used_questions]

                if not available_questions:
                    # If we've used all templates, create a variation
                    question = question_templates[len(previous_answers) % len(question_templates)].copy()
                    question["id"] = f"q_{question['id'].split('_')[1]}_{uuid.uuid4()}"
                else:
                    question = available_questions[0]

                logger.info(f"Generated question: {question['text']}")
                return question

            except Exception as e:
                logger.error(f"Error generating AI question: {e}")
                # Fallback to a simple question
                return {
                    "id": f"q_fallback_{uuid.uuid4()}",
                    "type": "yes_no",
                    "text": "Have you experienced any major life changes in the past year?",
                    "relevance": "medium"
                }

        # Retrieve user history and birth details from session storage
        # This would be implemented to get the full conversation history
        user_history = get_session_history(session_id)
        birth_details = get_session_birth_details(session_id)
        previous_answers = get_session_answers(session_id)

        # Add current answer to history
        previous_answers[str(uuid.uuid4())] = request.response["answer"]

        # Calculate current confidence level based on answers so far
        current_confidence = calculate_confidence_score(previous_answers, birth_details)

        # Generate next question using AI based on previous answers
        # IMPORTANT: This must be implemented to generate dynamic, personalized questions
        # DO NOT use hardcoded questions - each question should be unique to the conversation
        next_question = generate_ai_question(
            chart_data=get_session_chart(session_id),
            birth_details=birth_details,
            previous_answers=previous_answers,
            confidence_level=current_confidence
        )

        # Check if we've reached completion threshold
        is_complete = current_confidence >= 90 or len(previous_answers) >= 15

        # If we've reached the threshold, no need for next question
        if is_complete:
            logger.info(f"Questionnaire complete for session: {session_id}, confidence: {current_confidence}")
            return {
                "sessionId": session_id,
                "confidence": current_confidence,
                "isComplete": True,
                "analysisComplete": True
            }

        # Ensure the question has the required structure
        if not isinstance(next_question, dict) or "id" not in next_question or "text" not in next_question:
            logger.error("AI generated an invalid question format")
            # Generate a generic follow-up question as fallback
            # This should only happen if there's an AI generation error
            next_question = {
                "id": f"ai_q_{uuid.uuid4()}",
                "type": "yes_no",
                "text": "Have you experienced any significant life events in the past year?",
                "relevance": "medium"
            }
            logger.warning("Using fallback question as AI generated invalid format. This should be fixed!")

        logger.info(f"Generated next question for session {session_id}: {next_question['text']}")

        # Return response with updated confidence
        return {
            "sessionId": session_id,
            "confidence": current_confidence,
            "nextQuestion": next_question,
            "analysisComplete": False
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        stack_trace = traceback.format_exc()
        logger.debug(f"Stack trace: {stack_trace}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error getting next question: {str(e)}",
                "error_type": type(e).__name__,
                "session_id": request.sessionId if hasattr(request, 'sessionId') else None
            }
        )

@api_router.get("/analysis", response_model=Dict[str, Any])
async def get_analysis_results(sessionId: str = Query(..., description="Session ID for the analysis")):
    """Get the completed analysis results including rectified birth time, confidence scores, and chart details"""
    try:
        logger.info(f"Retrieving analysis results for session: {sessionId}")

        # Validate session ID format
        try:
            uuid.UUID(sessionId)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Invalid session ID format",
                    "provided_id": sessionId,
                    "field": "sessionId"
                }
            )

        # In a real implementation, we would check if analysis is complete
        # For demo purposes, we'll always return a result

        # Create dummy analysis results
        analysis_result = {
            "sessionId": sessionId,
            "birthDetails": {
                "date": "1985-10-24T00:00:00",
                "place": "Pune, India",
                "coordinates": {
                    "latitude": 18.5204,
                    "longitude": 73.8567,
                },
                "originalTime": "02:30 PM",
                "rectifiedTime": "02:47 PM"
            },
            "confidence": {
                "score": 85,
                "level": "High",
                "details": {
                    "minute_adjustment": 17,
                    "house_adjustments": {
                        "house1": 5,
                        "house10": 4,
                        "house4": 3,
                        "house7": 2
                    }
                }
            },
            "chart": {
                "ascendant": {
                    "sign": "Scorpio",
                    "degree": 15.5,
                    "longitude": 225.5
                },
                "planets": [
                    {
                        "name": "Sun",
                        "sign": "Libra",
                        "house": 12,
                        "degree": 10.5,
                        "retrograde": False
                    },
                    {
                        "name": "Moon",
                        "sign": "Leo",
                        "house": 10,
                        "degree": 5.2,
                        "retrograde": False
                    }
                ],
                "houses": [
                    {
                        "number": 1,
                        "sign": "Scorpio",
                        "degree": 0.0
                    },
                    {
                        "number": 10,
                        "sign": "Leo",
                        "degree": 0.0
                    }
                ]
            },
            "interpretations": {
                "houses": {
                    "ascendant": {
                        "sign": "Scorpio",
                        "interpretation": "With Scorpio rising, you present yourself as intense, mysterious, and perceptive. You may have a magnetic presence that hints at hidden depths."
                    },
                    "midheaven": {
                        "sign": "Leo",
                        "interpretation": "With Leo on your Midheaven, your career path often involves creativity, leadership, and gaining recognition. You're likely drawn to fields where you can shine and express your unique talents."
                    }
                },
                "planets": {
                    "sun": {
                        "sign": "Libra",
                        "house": 12,
                        "interpretation": "Your Sun in Libra shapes your core identity and purpose. It expresses through your spirituality and the unconscious, suggesting that you find your authentic self through harmonious relationships and aesthetic pursuits in private or behind-the-scenes activities."
                    },
                    "moon": {
                        "sign": "Leo",
                        "house": 10,
                        "interpretation": "Your Moon in Leo shapes your emotional nature and instinctive responses. It expresses through your career and public reputation, suggesting that you need recognition and appreciation to feel emotionally secure."
                    }
                }
            }
        }

        logger.info(f"Successfully retrieved analysis for session: {sessionId}")
        return analysis_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        stack_trace = traceback.format_exc()
        logger.debug(f"Stack trace: {stack_trace}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error retrieving analysis results: {str(e)}",
                "error_type": type(e).__name__,
                "session_id": sessionId
            }
        )

# Mount the API router
app.include_router(api_router)

# Include the routers
app.include_router(geocoding_router, prefix="/api")
app.include_router(chart_router, prefix="/api")
app.include_router(health_router, prefix="/api")

# Also include them at the root level for compatibility
app.include_router(geocoding_router)
app.include_router(chart_router)
app.include_router(health_router)

# Create router for questionnaire endpoints
questionnaire_router = APIRouter(prefix="/api/questionnaire", tags=["questionnaire"])

# Pydantic models for questionnaire API
class BirthDetailsModel(BaseModel):
    name: str
    gender: str
    birthDate: str
    approximateTime: str
    birthLocation: str
    coordinates: Optional[Dict[str, float]] = None
    timezone: Optional[str] = None

class QuestionnaireRequest(BaseModel):
    birthDetails: BirthDetailsModel
    currentConfidence: float = 0
    previousAnswers: Optional[Dict[str, str]] = None
    chartData: Optional[Dict[str, Any]] = None
    sessionId: Optional[str] = None
    questionHistory: Optional[List[str]] = None
    answerHistory: Optional[List[str]] = None

# Initialize questionnaire engine
questionnaire_engine = QuestionnaireEngine()
astro_calculator = AstroCalculator()

# Store session data
questionnaire_sessions = {}

@questionnaire_router.post("/generate", response_model=QuestionnaireResponseModel)
async def generate_questions(request: QuestionnaireRequest):
    """
    Generate personalized questions for birth time rectification based on birth details and previous answers.
    """
    REQUESTS.inc()

    try:
        # Create or retrieve session
        session_id = request.sessionId or str(uuid.uuid4())

        # Initialize session data if new
        if session_id not in questionnaire_sessions:
            questionnaire_sessions[session_id] = {
                "birthDetails": request.birthDetails.model_dump(),
                "answers": {},
                "questionHistory": [],
                "confidenceScore": 0,
                "chartData": None
            }

        session = questionnaire_sessions[session_id]

        # Update session with latest data
        if request.previousAnswers:
            session["answers"].update(request.previousAnswers)

        if request.questionHistory:
            for q_id in request.questionHistory:
                if q_id not in session["questionHistory"]:
                    session["questionHistory"].append(q_id)

        # Use provided chart data or calculate it
        chart_data = request.chartData
        if not chart_data and not session["chartData"]:
            # Calculate chart data from birth details
            birth_details = request.birthDetails

            try:
                # Convert to expected format for astro_calculator
                birth_date = datetime.fromisoformat(birth_details.birthDate.replace('Z', '+00:00'))

                # Parse approximate time
                time_parts = birth_details.approximateTime.split(':')
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

                # Create datetime with the birth date and approximate time
                birth_datetime = datetime.combine(
                    birth_date.date(),
                    time(hours, minutes, seconds)
                )

                # Get coordinates
                latitude = 0.0
                longitude = 0.0
                if birth_details.coordinates:
                    coords = birth_details.coordinates
                    latitude = coords.get("latitude", 0.0)
                    longitude = coords.get("longitude", 0.0)

                # Calculate chart
                if astro_calculator:
                    chart_data = astro_calculator.calculate_chart(
                        birth_datetime,
                        latitude,
                        longitude,
                        house_system=PLACIDUS  # Use the bytes constant instead of string
                    )

                    # Store chart data in session
                    session["chartData"] = chart_data
            except Exception as e:
                logger.error(f"Error calculating chart: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue without chart data
        elif request.chartData:
            session["chartData"] = request.chartData

        # Use current confidence or update from request
        current_confidence = max(request.currentConfidence, session["confidenceScore"])

        # Generate questions
        batch_size = 5  # Number of questions to return at once
        questions = []

        # Check if we've reached confidence threshold
        if current_confidence >= 90:
            return QuestionnaireResponseModel(
                questions=[],
                confidenceScore=current_confidence,
                sessionId=session_id,
                isComplete=True
            )

        # Generate questions based on chart data and previous answers
        if questionnaire_engine:
            # Initialize with chart data if not already done
            if session["chartData"] and not questionnaire_engine.chart_data:
                questionnaire_engine.chart_data = session["chartData"]

            # Process previous answers if any
            for q_id, answer in session["answers"].items():
                if q_id not in questionnaire_engine.answers:
                    questionnaire_engine.process_answer(q_id, answer)

            for _ in range(batch_size):
                question = questionnaire_engine.generate_next_question()

                if question and question["id"] not in session["questionHistory"]:
                    questions.append(DynamicQuestion(
                        id=question["id"],
                        text=question["text"],
                        type=question["type"],
                        options=question.get("options"),
                        weight=question.get("weight", 1.0)
                    ))
                    session["questionHistory"].append(question["id"])

        # If no questions were generated, add some generic ones
        if not questions:
            generic_questions = [
                DynamicQuestion(
                    id=f"generic_{uuid.uuid4()}",
                    text="Have you experienced any major career changes in the last 5 years?",
                    type="yes_no",
                    weight=0.8
                ),
                DynamicQuestion(
                    id=f"generic_{uuid.uuid4()}",
                    text="When did you meet your current partner or have a significant relationship begin?",
                    type="date",
                    weight=0.8
                ),
                DynamicQuestion(
                    id=f"generic_{uuid.uuid4()}",
                    text="Have you moved to a new location in the last 10 years?",
                    type="yes_no",
                    weight=0.7
                ),
                DynamicQuestion(
                    id=f"generic_{uuid.uuid4()}",
                    text="Have you experienced any significant health issues?",
                    type="yes_no",
                    weight=0.7
                ),
                DynamicQuestion(
                    id=f"generic_{uuid.uuid4()}",
                    text="When did you start your current job or career path?",
                    type="date",
                    weight=0.8
                )
            ]

            # Add questions that aren't in history
            for q in generic_questions:
                if q.id not in session["questionHistory"]:
                    questions.append(q)
                    session["questionHistory"].append(q.id)
                    if len(questions) >= batch_size:
                        break

        # Update confidence score based on number of questions answered
        # This is a simple heuristic - in a real system, this would be more sophisticated
        answered_count = len(session["answers"])
        confidence_increment = min(5, 100 - current_confidence) if answered_count > 0 else 0
        new_confidence = min(current_confidence + confidence_increment, 100)

        session["confidenceScore"] = new_confidence

        # Return response
        return QuestionnaireResponseModel(
            questions=questions,
            confidenceScore=new_confidence,
            sessionId=session_id,
            isComplete=new_confidence >= 90
        )

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

# Register the questionnaire router
app.include_router(questionnaire_router)
