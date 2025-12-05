'use client';

import type { Sample } from '@/lib/types';
import { formatScore } from '@/lib/utils';
import { useState, Fragment } from 'react';

interface Props {
  samples: Sample[];
}

export function SamplesTable({ samples }: Props) {
  const [expandedSamples, setExpandedSamples] = useState<Set<string | number>>(
    new Set()
  );

  const toggleSample = (id: string | number) => {
    const newExpanded = new Set(expandedSamples);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedSamples(newExpanded);
  };

  const renderValue = (value: unknown): string => {
    if (value === undefined || value === null) return '-';
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      if (value.every((v) => typeof v === 'string')) {
        return value.join(', ');
      }
      return JSON.stringify(value, null, 2);
    }
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const truncateText = (text: string, maxLength: number = 100): string => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
  };

  if (samples.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
        No samples available
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Input
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Target
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Extracted
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Prediction
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Scores
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {samples.map((sample, index) => {
              const isExpanded = expandedSamples.has(sample.id);
              const inputText = renderValue(sample.input);
              const targetText = renderValue(sample.target);
              const predictionText = renderValue(sample.prediction);
              const extractedText = sample.extracted_prediction || '';
              const displayId = sample.id ?? `sample-${index}`;

              return (
                <Fragment key={sample.id}>
                  <tr
                    className="hover:bg-gray-50 cursor-pointer"
                    onDoubleClick={() => toggleSample(sample.id)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {displayId}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs">
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                          {isExpanded ? inputText : truncateText(inputText)}
                        </pre>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs">
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                          {isExpanded ? targetText : truncateText(targetText)}
                        </pre>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs">
                        {extractedText ? (
                          <span className="inline-flex px-2 py-1 rounded bg-blue-50 text-blue-700 font-medium">
                            {isExpanded ? extractedText : truncateText(extractedText, 50)}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs">
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                          {isExpanded
                            ? predictionText
                            : truncateText(predictionText)}
                        </pre>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {Object.entries(sample.scores || {})
                        .filter(([_, value]) => {
                          // Filter out invalid scores
                          return value !== undefined && value !== null && !isNaN(value);
                        })
                        .map(([key, value]) => {
                          const numValue = typeof value === 'number' ? value : parseFloat(String(value));
                          if (isNaN(numValue)) return null;
                          return (
                            <div key={key} className="mb-1">
                              <span className="text-gray-500">{key}:</span>{' '}
                              <span
                                className={`font-medium ${
                                  numValue >= 0.5 ? 'text-green-600' : 'text-red-600'
                                }`}
                              >
                                {formatScore(numValue)}
                              </span>
                            </div>
                          );
                        })
                        .filter(Boolean)}
                      {Object.keys(sample.scores || {}).length === 0 && (
                        <span className="text-gray-400 text-xs">No scores</span>
                      )}
                      {sample.is_correct !== undefined && (
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium mt-1 ${
                            sample.is_correct
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {sample.is_correct ? 'Correct' : 'Wrong'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => toggleSample(sample.id)}
                        className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium"
                      >
                        {isExpanded ? 'Collapse' : 'Expand'}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${sample.id}-details`}>
                      <td colSpan={7} className="px-6 py-4 bg-gray-50">
                        <div className="space-y-4">
                          {sample.choices && sample.choices.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                                Choices
                              </h4>
                              <ul className="list-disc list-inside text-sm text-gray-900">
                                {sample.choices.map((choice, idx) => (
                                  <li key={idx}>{choice}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {sample.metadata &&
                            Object.keys(sample.metadata).length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                                  Metadata
                                </h4>
                                <pre className="text-xs text-gray-900 bg-white p-3 rounded border border-gray-200 overflow-x-auto">
                                  {JSON.stringify(sample.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
