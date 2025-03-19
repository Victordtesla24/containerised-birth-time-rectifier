from ai_service.services.chart_service import get_chart_service
from ai_service.api.services.questionnaire_service import get_questionnaire_service
import asyncio

async def test():
    # Generate chart
    chart_service = get_chart_service()
    chart_data = await chart_service.calculate_chart(
        birth_details={
            'birth_date': '1990-01-01',
            'birth_time': '12:00',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'timezone': 'America/New_York'
        },
        options={
            'house_system': 'P',
            'verify_with_openai': False
        }
    )
    
    # Get chart ID
    chart_id = chart_data['chart_id']
    print(f'Generated chart with ID: {chart_id}')
    
    # Get questionnaire service
    questionnaire_service = get_questionnaire_service()
    
    # Generate next question
    birth_details = {
        'birthDate': '1990-01-01', 
        'birthTime': '12:00',
        'birthPlace': 'New York, NY',
        'latitude': 40.7128,
        'longitude': -74.0060
    }
    
    # Get next question
    next_question = await questionnaire_service.generate_next_question(birth_details, {})
    print('Next question:')
    print(next_question)

asyncio.run(test())
