from ai_service.core.chart_calculator import get_enhanced_chart_calculator, calculate_verified_chart
import asyncio

async def test():
    calc = get_enhanced_chart_calculator()
    result = await calculate_verified_chart(birth_date='1990-01-01', birth_time='12:00', latitude=40.7128, longitude=-74.0060)
    print(result)

asyncio.run(test())
