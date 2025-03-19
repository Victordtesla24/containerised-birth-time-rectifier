from ai_service.core.chart_calculator import get_enhanced_chart_calculator
import inspect

calc = get_enhanced_chart_calculator()
print('Methods:')
for method_name in dir(calc):
    if not method_name.startswith('_'):
        print(f'- {method_name}')
