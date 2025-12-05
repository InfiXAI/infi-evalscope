'use client';

import type { DatasetEvaluation } from '@/lib/types';
import { formatScore } from '@/lib/utils';

interface Props {
  results: DatasetEvaluation[];
}

export function BenchmarkResultsTable({ results }: Props) {
  if (results.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
        No benchmark results available
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
                Dataset
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Overall Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Metrics
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Samples
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.dataset} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {result.dataset_pretty_name || result.dataset}
                  </div>
                  {result.dataset_pretty_name && (
                    <div className="text-xs text-gray-500">{result.dataset}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-lg font-semibold text-gray-900">
                    {formatScore(result.overall_score)}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.metrics).map(([name, value]) => (
                      <span
                        key={name}
                        className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100"
                      >
                        <span className="text-gray-600">{name}:</span>
                        <span className="ml-1 font-medium text-gray-900">
                          {formatScore(value.score)}
                        </span>
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {Object.values(result.metrics)[0]?.num_samples?.toLocaleString() ||
                    'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.some((r) => r.categories.length > 0) && (
        <div className="border-t border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Category Breakdown
          </h3>
          <div className="space-y-6">
            {results.map(
              (result) =>
                result.categories.length > 0 && (
                  <div key={result.dataset}>
                    <h4 className="text-md font-medium text-gray-700 mb-3">
                      {result.dataset}
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {result.categories.map((cat, idx) => (
                        <div
                          key={idx}
                          className="bg-gray-50 rounded-lg p-3 border border-gray-200"
                        >
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium text-gray-900">
                              {Array.isArray(cat.name)
                                ? cat.name.join(' > ')
                                : cat.name}
                            </span>
                            <span className="text-sm font-bold text-blue-600">
                              {formatScore(cat.score)}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {cat.num_samples} samples
                          </div>
                          {cat.subsets.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {cat.subsets.slice(0, 3).map((subset, subIdx) => (
                                <div
                                  key={subIdx}
                                  className="flex justify-between text-xs"
                                >
                                  <span className="text-gray-600">
                                    {subset.name}
                                  </span>
                                  <span className="text-gray-900">
                                    {formatScore(subset.score)}
                                  </span>
                                </div>
                              ))}
                              {cat.subsets.length > 3 && (
                                <div className="text-xs text-gray-400">
                                  +{cat.subsets.length - 3} more
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
