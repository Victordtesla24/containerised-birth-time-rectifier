import React from 'react';

interface Correction {
  field: string;
  original: string | number;
  corrected: string | number;
  explanation?: string;
}

interface VerificationData {
  status: string;
  confidence: number;
  corrections_applied: boolean;
  corrections?: Correction[];
  message: string;
}

interface ChartVerificationProps {
  verification: VerificationData;
  className?: string;
}

/**
 * Component to display chart verification results from OpenAI
 */
const ChartVerification: React.FC<ChartVerificationProps> = ({ verification, className = '' }) => {
  if (!verification) {
    return null;
  }

  const { status, confidence, corrections_applied, corrections = [], message } = verification;

  // Determine status color
  const getStatusColor = () => {
    switch (status) {
      case 'verified':
        return 'text-green-600';
      case 'errors_found':
        return 'text-yellow-600';
      case 'verification_error':
        return 'text-red-600';
      case 'not_verified':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  // Determine confidence level text
  const getConfidenceLevel = () => {
    if (confidence >= 90) return 'Very High';
    if (confidence >= 75) return 'High';
    if (confidence >= 60) return 'Moderate';
    if (confidence >= 40) return 'Low';
    return 'Very Low';
  };

  // Format status for display
  const formatStatus = (status: string) => {
    switch (status) {
      case 'verified':
        return 'Verified';
      case 'errors_found':
        return 'Errors Found';
      case 'verification_error':
        return 'Verification Error';
      case 'not_verified':
        return 'Not Verified';
      default:
        return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };

  return (
    <div className={`chart-verification p-4 border rounded-lg shadow-sm ${className}`}>
      <h3 className="text-lg font-semibold mb-2">Chart Verification</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <div className="mb-2">
            <span className="font-medium">Status: </span>
            <span className={`font-semibold ${getStatusColor()}`}>
              {formatStatus(status)}
            </span>
          </div>

          <div className="mb-2">
            <span className="font-medium">Confidence: </span>
            <span className="font-semibold">
              {confidence.toFixed(1)}% ({getConfidenceLevel()})
            </span>
          </div>

          <div>
            <span className="font-medium">Corrections Applied: </span>
            <span className="font-semibold">
              {corrections_applied ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        <div>
          <div className="font-medium mb-1">Verification Message:</div>
          <p className="text-sm text-gray-700">{message}</p>
        </div>
      </div>

      {corrections && corrections.length > 0 && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">Corrections:</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-2 text-left">Field</th>
                  <th className="px-4 py-2 text-left">Original</th>
                  <th className="px-4 py-2 text-left">Corrected</th>
                  <th className="px-4 py-2 text-left">Explanation</th>
                </tr>
              </thead>
              <tbody>
                {corrections.map((correction, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-4 py-2 font-medium">{correction.field}</td>
                    <td className="px-4 py-2">{correction.original}</td>
                    <td className="px-4 py-2">{correction.corrected}</td>
                    <td className="px-4 py-2 text-gray-600">{correction.explanation || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {status === 'verified' && confidence >= 90 && (
        <div className="mt-4 p-2 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
          <span className="font-semibold">✓ Verified:</span> This chart has been verified with high confidence and meets Vedic astrological standards.
        </div>
      )}

      {status === 'errors_found' && (
        <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
          <span className="font-semibold">⚠️ Warning:</span> This chart has some potential errors or inconsistencies. Review the corrections for details.
        </div>
      )}

      {status === 'verification_error' && (
        <div className="mt-4 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          <span className="font-semibold">❌ Error:</span> There was a problem verifying this chart. The calculations may still be accurate, but could not be verified.
        </div>
      )}
    </div>
  );
};

export default ChartVerification;
