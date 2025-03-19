from ai_service.services.chart_service import get_chart_service
import asyncio

async def test():
    chart_service = get_chart_service()
    result = await chart_service.calculate_chart(
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
    print(result)

asyncio.run(test())
