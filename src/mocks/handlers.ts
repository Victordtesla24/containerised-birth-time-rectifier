import { http, HttpResponse } from 'msw';

// Define handlers for API mocking
export const handlers = [
  // Mock for chart generation endpoint
  http.post('/api/charts', () => {
    return HttpResponse.json({
      ascendant: 0,
      planets: [
        { id: 'sun', position: 30, house: 1 },
        { id: 'moon', position: 60, house: 2 },
        { id: 'mercury', position: 90, house: 3 }
      ],
      houses: [
        { number: 1, start: 0, end: 30 },
        { number: 2, start: 30, end: 60 },
        { number: 3, start: 60, end: 90 }
      ],
      divisionalCharts: {}
    });
  }),
  
  // Mock for birth time rectification endpoint
  http.post('/api/rectify', () => {
    return HttpResponse.json({
      suggestedTime: '12:30:00',
      confidence: 0.85,
      details: {
        ascendantChange: true,
        houseShifts: [1, 3, 5]
      }
    });
  }),
  
  // Mock for questionnaire endpoint
  http.get('/api/questionnaire', () => {
    return HttpResponse.json([
      {
        id: 'q1',
        text: 'Do you have any major career changes?',
        type: 'boolean'
      },
      {
        id: 'q2',
        text: 'When did you get married?',
        type: 'date'
      }
    ]);
  }),
  
  // Add more handlers as needed for your tests
]; 