import React from 'react';
import { DynamicQuestion, QuestionOption } from '@/types';

interface MultipleChoiceQuestionProps {
  question: DynamicQuestion;
  value: string;
  onChange: (answer: string) => void;
}

const MultipleChoiceQuestion: React.FC<MultipleChoiceQuestionProps> = ({
  question,
  value,
  onChange
}) => {
  // Handle different option formats (string[] or QuestionOption[])
  const renderOptions = () => {
    if (!question.options || question.options.length === 0) {
      return <p className="text-red-500">No options available</p>;
    }

    // Check if options are strings or objects
    const firstOption = question.options[0];

    if (typeof firstOption === 'string') {
      // Options are strings
      return (
        <div className="grid grid-cols-1 gap-3">
          {question.options.map((option, index) => (
            <button
              key={index}
              type="button"
              onClick={() => onChange(option as string)}
              className={`py-3 px-4 rounded-lg text-left transition-colors ${
                value === option
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
              }`}
            >
              {option as string}
            </button>
          ))}
        </div>
      );
    } else {
      // Options are objects with id and text
      return (
        <div className="grid grid-cols-1 gap-3">
          {question.options.map((option, index) => {
            const typedOption = option as QuestionOption;
            return (
              <button
                key={typedOption.id || index}
                type="button"
                onClick={() => onChange(typedOption.text)}
                className={`py-3 px-4 rounded-lg text-left transition-colors ${
                  value === typedOption.text
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                }`}
              >
                {typedOption.text}
              </button>
            );
          })}
        </div>
      );
    }
  };

  return (
    <div className="multiple-choice-question">
      <h3 className="text-xl font-medium text-gray-800 mb-6">{question.text}</h3>
      {renderOptions()}
    </div>
  );
};

export default MultipleChoiceQuestion;
