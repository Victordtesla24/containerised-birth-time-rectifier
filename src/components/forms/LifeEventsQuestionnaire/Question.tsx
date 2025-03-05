import React from 'react';
import { QuestionResponse } from './types';

interface QuestionProps {
  question: QuestionResponse;
  onAnswerSelect: (answerId: string) => void;
}

const Question: React.FC<QuestionProps> = ({ question, onAnswerSelect }) => {
  return (
    <div className="question-container">
      <h3 className="question-text">{question.text}</h3>
      <div className="options-container">
        {question.options.map((option) => (
          <button
            key={option.id}
            className="option-button"
            onClick={() => onAnswerSelect(option.id)}
          >
            {option.text}
          </button>
        ))}
      </div>
    </div>
  );
};

export default Question;
