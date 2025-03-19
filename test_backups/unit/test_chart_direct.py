from ai_service.core.chart_calculator import calculate_chart
import json
import asyncio

def test():
    result = calculate_chart(
        birth_date='1990-01-01',
        birth_time='12:00',
        latitude=40.7128,
        longitude=-74.0060,
        location='New York, NY',
        house_system='P',
        ayanamsa=23.6647,
        node_type='true'
    )
    print(json.dumps(result, indent=2))

test()
