"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { Search, X, CheckCircle, XCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pagination } from "@/components/Pagination";
import { SamplesTable } from "@/components/SamplesTable";
import type { Sample } from "@/lib/types";

interface SamplesPageClientProps {
  runId: string;
  dataset: string;
  datasets: string[];
  samples: Sample[];
  modelName: string;
}

export function SamplesPageClient({
  runId,
  dataset,
  datasets,
  samples,
  modelName,
}: SamplesPageClientProps) {
  const [search, setSearch] = useState("");
  const [correctFilter, setCorrectFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Stats
  const stats = useMemo(() => {
    const correct = samples.filter((s) => s.is_correct === true).length;
    const incorrect = samples.filter((s) => s.is_correct === false).length;
    return { total: samples.length, correct, incorrect };
  }, [samples]);

  // Filter samples
  const filteredSamples = useMemo(() => {
    let result = [...samples];

    // Apply search
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter((s) => {
        const input =
          typeof s.input === "string"
            ? s.input
            : JSON.stringify(s.input);
        const target =
          typeof s.target === "string"
            ? s.target
            : Array.isArray(s.target)
              ? s.target.join(" ")
              : "";
        const prediction = s.prediction || s.extracted_prediction || "";
        return (
          input.toLowerCase().includes(searchLower) ||
          target.toLowerCase().includes(searchLower) ||
          prediction.toLowerCase().includes(searchLower)
        );
      });
    }

    // Apply correct/incorrect filter
    if (correctFilter === "correct") {
      result = result.filter((s) => s.is_correct === true);
    } else if (correctFilter === "incorrect") {
      result = result.filter((s) => s.is_correct === false);
    }

    return result;
  }, [samples, search, correctFilter]);

  // Paginate
  const paginatedSamples = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredSamples.slice(start, start + pageSize);
  }, [filteredSamples, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredSamples.length / pageSize);

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setCurrentPage(1);
  }, []);

  const handleFilterChange = useCallback((value: string) => {
    setCorrectFilter(value);
    setCurrentPage(1);
  }, []);

  const handleReset = useCallback(() => {
    setSearch("");
    setCorrectFilter("all");
    setCurrentPage(1);
  }, []);

  const hasActiveFilters = search !== "" || correctFilter !== "all";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Link */}
      <div className="mb-4">
        <Link href={`/runs/${runId}`}>
          <Button variant="ghost" size="sm" className="text-gray-600 hover:text-gray-900 hover:bg-gray-100">
            ← Back to run details
          </Button>
        </Link>
      </div>

      {/* Header */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">
                Sample Predictions
              </h1>
              <p className="text-gray-500">
                {modelName} - <span className="font-medium">{dataset}</span>
              </p>
            </div>
            <div className="flex gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                <p className="text-xs text-gray-500">Total</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {stats.correct}
                </p>
                <p className="text-xs text-gray-500">Correct</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">
                  {stats.incorrect}
                </p>
                <p className="text-xs text-gray-500">Incorrect</p>
              </div>
            </div>
          </div>

          {/* Dataset Tabs */}
          <div className="flex flex-wrap gap-2">
            {datasets.map((d) => (
              <Link key={d} href={`/runs/${runId}/samples?dataset=${d}`}>
                <Badge
                  variant={d === dataset ? "default" : "secondary"}
                  className={`cursor-pointer transition-colors ${
                    d === dataset
                      ? ""
                      : "hover:bg-gray-200 hover:text-gray-900"
                  }`}
                >
                  {d}
                </Badge>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="text-sm font-medium text-gray-700 mb-1.5 block">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search in input, target, or prediction..."
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          <div className="w-[150px]">
            <label className="text-sm font-medium text-gray-700 mb-1.5 block">
              Result
            </label>
            <Select value={correctFilter} onValueChange={handleFilterChange}>
              <SelectTrigger>
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Results</SelectItem>
                <SelectItem value="correct">
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-green-600" />
                    Correct
                  </span>
                </SelectItem>
                <SelectItem value="incorrect">
                  <span className="flex items-center gap-1">
                    <XCircle className="h-3 w-3 text-red-600" />
                    Incorrect
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="text-gray-500"
            >
              <X className="h-4 w-4 mr-1" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        {filteredSamples.length === samples.length
          ? `${samples.length} samples`
          : `${filteredSamples.length} of ${samples.length} samples`}
      </div>

      {/* Samples Table */}
      {paginatedSamples.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500">No samples match your filters</p>
        </div>
      ) : (
        <SamplesTable samples={paginatedSamples} />
      )}

      {/* Pagination */}
      {filteredSamples.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={filteredSamples.length}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setCurrentPage(1);
          }}
          pageSizeOptions={[10, 20, 50, 100]}
        />
      )}
    </div>
  );
}
