import React, { useState } from 'react';
import { DynamicQuestion } from '@/types';

interface TextQuestionProps {
  question: DynamicQuestion;
  value: string;
  onChange: (answer: string) => void;
}

const TextQuestion: React.FC<TextQuestionProps> = ({ question, value, onChange }) => {
  const [localValue, setLocalValue] = useState(value);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalValue(e.target.value);
  };

  const handleBlur = () => {
    if (localValue.trim()) {
      onChange(localValue);
    }
  };

  const handleSubmit = () => {
    if (localValue.trim()) {
      onChange(localValue);
    }
  };

  return (
    <div className="text-question">
      <h3 className="text-xl font-medium text-gray-800 mb-6">{question.text}</h3>

      <div className="mt-2">
        <textarea
          value={localValue}
          onChange={handleChange}
          onBlur={handleBlur}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          rows={5}
          placeholder="Enter your answer here..."
        />

        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!localValue.trim()}
            className={`px-4 py-2 rounded-md ${
              !localValue.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            Confirm Answer
          </button>
        </div>
      </div>
    </div>
  );
};

export default TextQuestion;
