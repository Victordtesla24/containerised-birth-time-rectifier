from ai_service.api.routers import questionnaire
import inspect

# Check what routes are available
print('Routes:')
for attr in dir(questionnaire):
    if attr.startswith('router'):
        router = getattr(questionnaire, attr)
        print(f'Router methods:')
        for route in router.routes:
            print(f'- {route}')
