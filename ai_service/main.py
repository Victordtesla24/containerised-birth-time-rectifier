from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from datetime import datetime
from typing import Union, Dict, List, Optional
from pydantic import BaseModel, Field

# Import routers
from ai_service.api.routers import health_router, chart_router, questionnaire_router, geocoding_router, auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("birth-time-rectifier")

# Create FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for astrological chart generation and birth time rectification",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Include health router at root level for easy monitoring access
app.include_router(health_router)

# Include individual routers twice - once with /api prefix and once at root level
# This ensures both /api/charts/* and /charts/* work, providing backward compatibility
# and fixing the API router issue

# With /api prefix
app.include_router(chart_router, prefix="/api/charts", tags=["charts"])
app.include_router(questionnaire_router, prefix="/api/questionnaire", tags=["questionnaire"])
app.include_router(geocoding_router, prefix="/api/geocoding", tags=["geocoding"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# At root level
app.include_router(chart_router, prefix="/charts", tags=["charts"])
app.include_router(questionnaire_router, prefix="/questionnaire", tags=["questionnaire"])
app.include_router(geocoding_router, prefix="/geocoding", tags=["geocoding"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Root endpoint for health check
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Birth Time Rectifier API",
    }

# Models for documentation
class PlanetPosition(BaseModel):
    planet: str
    sign: str
    degree: str
    house: int
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    speed: Optional[float] = None
    retrograde: Optional[bool] = None
    description: Optional[str] = None

class HouseData(BaseModel):
    number: int
    sign: str
    startDegree: float
    endDegree: float
    planets: List[PlanetPosition] = []

class Aspect(BaseModel):
    planet1: str
    planet2: str
    aspectType: str
    orb: float
    influence: str = Field(..., description="Influence can be 'positive', 'negative', or 'neutral'")
    description: Optional[str] = None

class ChartData(BaseModel):
    ascendant: Union[float, Dict[str, Union[str, float, None]]]
    planets: List[PlanetPosition]
    houses: List[HouseData]
    aspects: List[Aspect] = []

class QuestionOption(BaseModel):
    id: str
    text: str

class DynamicQuestion(BaseModel):
    id: str
    text: str
    type: str = Field(..., description="Question type can be 'yes_no', 'multiple_choice', 'date', or 'text'")
    options: Union[List[str], List[QuestionOption]] = []
    weight: float = 1.0

class QuestionAnswer(BaseModel):
    questionId: str
    question: str
    answer: str

class QuestionnaireResponse(BaseModel):
    answers: List[QuestionAnswer]
    confidenceScore: float
    sessionId: Optional[str] = None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
