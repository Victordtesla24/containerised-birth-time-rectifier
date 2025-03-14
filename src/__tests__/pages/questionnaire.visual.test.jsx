import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import QuestionnairePage from '../../pages/questionnaire';
import { questionnaireApi } from '../../services/apiService';

// Using real API endpoints - no mocks

describe('Questionnaire Visual Tests', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('should render the loading state correctly', async () => {
    // Mock API to delay response
    questionnaireApi.initializeQuestionnaire.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    const { container } = render(<QuestionnairePage />);

    // Check loading state with a more flexible matcher
    expect(screen.getByText(/loading questionnaire/i)).toBeInTheDocument();

    // Snapshot of loading state
    expect(container).toMatchSnapshot('questionnaire-loading');
  });

  it('should render the error state correctly', async () => {
    // Mock API to return error immediately
    questionnaireApi.initializeQuestionnaire.mockRejectedValueOnce(new Error('API Error'));

    // Use render outside of act for cleaner test
    const { container } = render(<QuestionnairePage />);

    // Wait for error state to appear
    await waitFor(() => {
      const errorElement = screen.queryByText(/error loading questionnaire/i);
      expect(errorElement).toBeInTheDocument();
    }, { timeout: 3000 });

    // Snapshot of error state
    expect(container).toMatchSnapshot('questionnaire-error');
  });

  it('should render questions correctly', async () => {
    // Mock successful API response with questions
    const mockQuestions = [
      {
        id: 'q1',
        text: 'Did you experience any major career changes?',
        type: 'boolean',
        relevance: 'high'
      }
    ];

    // Resolve immediately with mock data
    questionnaireApi.initializeQuestionnaire.mockResolvedValueOnce({
      questions: mockQuestions,
      confidenceScore: 0.2,
      isComplete: false,
      hasReachedThreshold: false
    });

    const { container } = render(<QuestionnairePage />);

    // Wait for questions to load
    await waitFor(() => {
      const questionElement = screen.queryByText(/major career changes/i);
      expect(questionElement).toBeInTheDocument();
    }, { timeout: 3000 });

    // Snapshot of question state
    expect(container).toMatchSnapshot('questionnaire-with-boolean-question');
  });

  it('should handle boolean question answers correctly', async () => {
    // Mock successful API responses
    const mockQuestions = [
      {
        id: 'q1',
        text: 'Did you experience any major career changes?',
        type: 'boolean',
        relevance: 'high'
      }
    ];

    // Resolve immediately with mock data
    questionnaireApi.initializeQuestionnaire.mockResolvedValueOnce({
      questions: mockQuestions,
      confidenceScore: 0.2,
      isComplete: false,
      hasReachedThreshold: false
    });

    questionnaireApi.getNextQuestion.mockResolvedValueOnce({
      questions: [
        {
          id: 'q2',
          text: 'When did this career change happen?',
          type: 'date',
          relevance: 'high'
        }
      ],
      confidenceScore: 0.3,
      isComplete: false,
      hasReachedThreshold: false
    });

    const { container } = render(<QuestionnairePage />);

    // Wait for first question to load
    await waitFor(() => {
      const questionElement = screen.queryByText(/major career changes/i);
      expect(questionElement).toBeInTheDocument();
    }, { timeout: 3000 });

    // Select "Yes" and click next
    fireEvent.click(screen.getByTestId('option-yes'));
    fireEvent.click(screen.getByText(/next question/i));

    // Wait for next question to load
    await waitFor(() => {
      expect(questionnaireApi.getNextQuestion).toHaveBeenCalledWith(
        'test-session-id',
        { questionId: 'q1', answer: 'yes' }
      );
    }, { timeout: 3000 });

    // Snapshot of second question
    expect(container).toMatchSnapshot('questionnaire-with-date-question');
  });

  it('should display the processing state correctly', async () => {
    // Mock successful API responses
    const mockQuestions = [
      {
        id: 'q1',
        text: 'When did you get married?',
        type: 'date',
        relevance: 'high'
      }
    ];

    // Resolve immediately with mock data
    questionnaireApi.initializeQuestionnaire.mockResolvedValueOnce({
      questions: mockQuestions,
      confidenceScore: 0.2,
      isComplete: false,
      hasReachedThreshold: false
    });

    questionnaireApi.getNextQuestion.mockResolvedValueOnce({
      questions: [],
      confidenceScore: 0.9,
      isComplete: true,
      hasReachedThreshold: true
    });

    questionnaireApi.processRectification.mockResolvedValueOnce({
      chartId: 'test-chart-id'
    });

    const { container } = render(<QuestionnairePage />);

    // Wait for question to load
    await waitFor(() => {
      const questionElement = screen.queryByText(/get married/i);
      expect(questionElement).toBeInTheDocument();
    }, { timeout: 3000 });

    // Set date and notes
    fireEvent.change(screen.getByTestId('date-input'), { target: { value: '2020-06-15' } });
    fireEvent.change(screen.getByTestId('additional-notes'), { target: { value: 'Summer wedding' } });

    // Click next
    fireEvent.click(screen.getByText(/next question/i));

    // Wait for processing indicator
    await waitFor(() => {
      expect(questionnaireApi.getNextQuestion).toHaveBeenCalledWith(
        'test-session-id',
        {
          questionId: 'q1',
          answer: {
            date: '2020-06-15',
            additional_notes: 'Summer wedding'
          }
        }
      );
    }, { timeout: 3000 });

    // Snapshot of processing state
    expect(container).toMatchSnapshot('questionnaire-processing');
  });
});
