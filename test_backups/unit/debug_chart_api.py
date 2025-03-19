@app.get("/api/v1/chart/{chart_id}")
async def debug_get_chart(chart_id: str):
    """Debug endpoint for retrieving a chart"""
    print(f"Getting chart with ID: {chart_id}")
    return {
        "chart_id": chart_id,
        "birth_details": {
            "date": "1990-01-15",
            "time": "14:30:00",
            "location": "New Delhi, India",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "timezone": "Asia/Kolkata"
        },
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "degree": 15.5},
            {"name": "Moon", "sign": "Libra", "degree": 22.3},
            {"name": "Mercury", "sign": "Capricorn", "degree": 10.1}
        ],
        "houses": [
            {"number": 1, "sign": "Cancer", "degree": 15.0},
            {"number": 2, "sign": "Leo", "degree": 10.2},
            {"number": 3, "sign": "Virgo", "degree": 8.5}
        ],
        "aspects": [
            {"planet1": "Sun", "planet2": "Moon", "aspect": "Square", "orb": 2.1}
        ],
        "verification": {
            "verified": True,
            "confidence": 95,
            "message": "Chart verified successfully"
        }
    }
