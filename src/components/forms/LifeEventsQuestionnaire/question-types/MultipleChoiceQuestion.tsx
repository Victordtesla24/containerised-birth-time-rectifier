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
  const renderOptions = () => {
    if (!question.options || question.options.length === 0) {
      return <p className="text-red-500">No options available</p>;
    }

    return (
      <div className="grid grid-cols-1 gap-3">
        {question.options.map((option, index) => {
          const optionText = typeof option === 'string' ? option : option.text;
          const optionId = typeof option === 'string' ? String(index) : option.id || String(index);

          return (
            <button
              key={optionId}
              type="button"
              onClick={() => onChange(optionText)}
              className={`py-3 px-4 rounded-lg text-left transition-colors ${
                value === optionText
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
              }`}
            >
              {optionText}
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div className="multiple-choice-question">
      <h3 className="text-xl font-medium text-gray-800 mb-6">{question.text}</h3>
      {renderOptions()}
    </div>
  );
};

export default MultipleChoiceQuestion;
