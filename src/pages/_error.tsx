import React from 'react';
import Head from 'next/head';

interface ErrorProps {
  statusCode?: number;
}

const Error = ({ statusCode }: ErrorProps) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Head>
        <title>Error - Birth Time Rectifier</title>
      </Head>
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
        <h1 className="text-2xl font-bold text-red-600 mb-4">
          {statusCode
            ? `An error ${statusCode} occurred on server`
            : 'An error occurred on client'}
        </h1>
        <p className="text-gray-600 mb-4">
          We apologize for the inconvenience. Please try refreshing the page or contact support if the problem persists.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded transition-colors"
        >
          Refresh Page
        </button>
      </div>
    </div>
  );
};

Error.getInitialProps = ({ res, err }: { res?: { statusCode: number }, err?: { statusCode: number } }) => {
  const statusCode = res ? res.statusCode : err ? err.statusCode : 404;
  return { statusCode };
};

export default Error;
