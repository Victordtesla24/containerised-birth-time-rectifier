import React from 'react';
import { DynamicQuestion } from '@/types';

interface DateQuestionProps {
  question: DynamicQuestion;
  value: string;
  onChange: (answer: string) => void;
}

const DateQuestion: React.FC<DateQuestionProps> = ({ question, value, onChange }) => {
  return (
    <div className="date-question">
      <h3 className="text-xl font-medium text-gray-800 mb-6">{question.text}</h3>

      <div className="mt-2">
        <input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          max={new Date().toISOString().split('T')[0]} // Prevent future dates
        />

        <p className="mt-2 text-sm text-gray-600">
          Please select the date that best corresponds to this event.
        </p>
      </div>
    </div>
  );
};

export default DateQuestion;
