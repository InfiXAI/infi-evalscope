"use client";

import { useState, useCallback } from "react";
import { Search, X, Filter } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface FilterState {
  search: string;
  status: string;
  sortBy: string;
  sortOrder: string;
}

interface RunsFilterProps {
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  datasets?: string[];
}

export function RunsFilter({
  filters,
  onFilterChange,
  datasets = [],
}: RunsFilterProps) {
  const [localSearch, setLocalSearch] = useState(filters.search);

  const handleSearchSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onFilterChange({ ...filters, search: localSearch });
    },
    [filters, localSearch, onFilterChange]
  );

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        onFilterChange({ ...filters, search: localSearch });
      }
    },
    [filters, localSearch, onFilterChange]
  );

  const handleReset = useCallback(() => {
    setLocalSearch("");
    onFilterChange({
      search: "",
      status: "all",
      sortBy: "start_time",
      sortOrder: "desc",
    });
  }, [onFilterChange]);

  const hasActiveFilters =
    filters.search !== "" ||
    filters.status !== "all" ||
    filters.sortBy !== "start_time" ||
    filters.sortOrder !== "desc";

  return (
    <div className="bg-white rounded-lg border p-4 mb-6">
      <div className="flex flex-wrap gap-4 items-end">
        {/* Search Input */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-medium text-gray-700 mb-1.5 block">
            Search Model
          </label>
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search by model name..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              className="pl-9 pr-4"
            />
          </form>
        </div>

        {/* Status Filter */}
        <div className="w-[150px]">
          <label className="text-sm font-medium text-gray-700 mb-1.5 block">
            Status
          </label>
          <Select
            value={filters.status}
            onValueChange={(value) =>
              onFilterChange({ ...filters, status: value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="running">Running</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Sort By */}
        <div className="w-[150px]">
          <label className="text-sm font-medium text-gray-700 mb-1.5 block">
            Sort By
          </label>
          <Select
            value={filters.sortBy}
            onValueChange={(value) =>
              onFilterChange({ ...filters, sortBy: value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="start_time">Start Time</SelectItem>
              <SelectItem value="overall_score">Score</SelectItem>
              <SelectItem value="duration_seconds">Duration</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Sort Order */}
        <div className="w-[130px]">
          <label className="text-sm font-medium text-gray-700 mb-1.5 block">
            Order
          </label>
          <Select
            value={filters.sortOrder}
            onValueChange={(value) =>
              onFilterChange({ ...filters, sortOrder: value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Order" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="desc">Descending</SelectItem>
              <SelectItem value="asc">Ascending</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-4 w-4 mr-1" />
            Reset
          </Button>
        )}
      </div>
    </div>
  );
}
