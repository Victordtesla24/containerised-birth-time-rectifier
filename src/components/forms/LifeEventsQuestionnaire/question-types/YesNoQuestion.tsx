import React from 'react';
import { DynamicQuestion } from '@/types';

interface YesNoQuestionProps {
  question: DynamicQuestion;
  value: string;
  onChange: (answer: string) => void;
}

const YesNoQuestion: React.FC<YesNoQuestionProps> = ({ question, value, onChange }) => {
  return (
    <div className="yes-no-question">
      <h3 className="text-xl font-medium text-gray-800 mb-6">{question.text}</h3>

      <div className="flex flex-col sm:flex-row gap-4">
        <button
          type="button"
          onClick={() => onChange('Yes')}
          className={`flex-1 py-4 px-6 rounded-lg text-center transition-colors ${
            value === 'Yes'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
          }`}
        >
          <span className="text-lg font-medium">Yes</span>
        </button>

        <button
          type="button"
          onClick={() => onChange('No')}
          className={`flex-1 py-4 px-6 rounded-lg text-center transition-colors ${
            value === 'No'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
          }`}
        >
          <span className="text-lg font-medium">No</span>
        </button>
      </div>
    </div>
  );
};

export default YesNoQuestion;
