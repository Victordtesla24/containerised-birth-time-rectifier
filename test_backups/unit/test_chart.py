from ai_service.core.astro_calculator import AstroCalculator
import asyncio

async def test():
    calc = AstroCalculator()
    result = await calc.calculate_chart(birth_date='1990-01-01', birth_time='12:00', latitude=40.7128, longitude=-74.0060, timezone='America/New_York')
    print(result)

asyncio.run(test())
