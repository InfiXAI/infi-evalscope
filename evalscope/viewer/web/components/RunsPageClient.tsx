"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { formatDate, formatDuration, formatScore } from "@/lib/utils";
import { RunsFilter, type FilterState } from "@/components/RunsFilter";
import { StatsCards } from "@/components/StatsCards";
import { Pagination } from "@/components/Pagination";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { RunIndexEntry } from "@/lib/types";

interface RunsPageClientProps {
  runs: RunIndexEntry[];
  lastUpdated?: string;
}

export function RunsPageClient({ runs, lastUpdated }: RunsPageClientProps) {
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    status: "all",
    sortBy: "start_time",
    sortOrder: "desc",
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Calculate stats
  const stats = useMemo(() => {
    const completedRuns = runs.filter((r) => r.status === "completed");
    const scoresWithValues = runs
      .map((r) => r.overall_score)
      .filter((s): s is number => s !== null && s !== undefined);

    const avgScore =
      scoresWithValues.length > 0
        ? scoresWithValues.reduce((a, b) => a + b, 0) / scoresWithValues.length
        : null;

    const successRate =
      runs.length > 0 ? completedRuns.length / runs.length : null;

    const sortedByTime = [...runs].sort(
      (a, b) =>
        new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
    );
    const lastRun = sortedByTime[0];
    const lastRunTime = lastRun
      ? getRelativeTime(new Date(lastRun.start_time))
      : null;

    return {
      totalRuns: runs.length,
      avgScore,
      successRate,
      lastRunTime,
    };
  }, [runs]);

  // Filter and sort runs
  const filteredRuns = useMemo(() => {
    let result = [...runs];

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      result = result.filter((r) => {
        const modelName = r.model?.name ?? "";
        return (
          modelName.toLowerCase().includes(searchLower) ||
          r.run_id.toLowerCase().includes(searchLower)
        );
      });
    }

    // Apply status filter
    if (filters.status !== "all") {
      result = result.filter((r) => r.status === filters.status);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aValue: string | number | null;
      let bValue: string | number | null;

      switch (filters.sortBy) {
        case "overall_score":
          aValue = a.overall_score ?? -1;
          bValue = b.overall_score ?? -1;
          break;
        case "duration_seconds":
          aValue = a.duration_seconds ?? -1;
          bValue = b.duration_seconds ?? -1;
          break;
        default:
          aValue = a.start_time;
          bValue = b.start_time;
      }

      if (aValue < bValue) return filters.sortOrder === "asc" ? -1 : 1;
      if (aValue > bValue) return filters.sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [runs, filters]);

  // Paginate
  const paginatedRuns = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRuns.slice(start, start + pageSize);
  }, [filteredRuns, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredRuns.length / pageSize);

  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setCurrentPage(1); // Reset to first page on filter change
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">
          Evaluation Runs
        </h1>
        <p className="text-gray-500 text-sm">
          {lastUpdated && `Last updated: ${formatDate(lastUpdated)}`}
        </p>
      </div>

      {/* Stats Cards */}
      <StatsCards {...stats} />

      {/* Filters */}
      <RunsFilter filters={filters} onFilterChange={handleFilterChange} />

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        {filteredRuns.length === runs.length
          ? `${runs.length} runs`
          : `${filteredRuns.length} of ${runs.length} runs`}
      </div>

      {/* Runs Grid */}
      {paginatedRuns.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500">No runs match your filters</p>
          <p className="text-gray-400 text-sm mt-2">
            Try adjusting your search criteria
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {paginatedRuns.map((run) => (
            <Link key={run.run_id} href={`/runs/${run.run_id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-gray-900 truncate">
                        {run.model?.name ?? "Unknown model"}
                      </h3>
                      <p className="text-xs text-gray-400 truncate">
                        {run.run_id}
                      </p>
                    </div>
                    <Badge
                      variant={
                        run.status === "completed"
                          ? "success"
                          : run.status === "failed"
                            ? "destructive"
                            : "warning"
                      }
                    >
                      {run.status}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
                    <div>
                      <p className="text-gray-400 text-xs">Score</p>
                      <p className="font-medium text-gray-900">
                        {formatScore(run.overall_score)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-xs">Duration</p>
                      <p className="font-medium text-gray-900">
                        {formatDuration(run.duration_seconds)}
                      </p>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 pt-3">
                    <div className="flex flex-wrap gap-1.5">
                      {run.datasets.slice(0, 4).map((dataset) => (
                        <span
                          key={dataset}
                          className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded"
                        >
                          {dataset}
                        </span>
                      ))}
                      {run.datasets.length > 4 && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                          +{run.datasets.length - 4}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 text-xs text-gray-400">
                    {formatDate(run.start_time)}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {filteredRuns.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={filteredRuns.length}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      )}
    </div>
  );
}

function getRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(date.toISOString());
}
