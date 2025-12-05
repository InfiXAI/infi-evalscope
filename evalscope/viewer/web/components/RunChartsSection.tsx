"use client";

import { DatasetScoreChart } from "@/components/charts/DatasetScoreChart";
import { CategoryRadarChart } from "@/components/charts/CategoryRadarChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DatasetEvaluation } from "@/lib/types";

interface RunChartsSectionProps {
  datasets: DatasetEvaluation[];
}

export function RunChartsSection({ datasets }: RunChartsSectionProps) {
  // Prepare data for dataset score chart
  const datasetScores = datasets.map((d) => ({
    dataset: d.dataset_pretty_name || d.dataset,
    score: d.overall_score,
  }));

  // Collect all categories across all datasets for radar chart
  const allCategories: { name: string; score: number; count: number }[] = [];
  datasets.forEach((d) => {
    d.categories?.forEach((cat) => {
      const catName = Array.isArray(cat.name) ? cat.name.join(" > ") : cat.name;
      const existing = allCategories.find((c) => c.name === catName);
      if (existing) {
        existing.score += cat.score;
        existing.count += 1;
      } else {
        allCategories.push({ name: catName, score: cat.score, count: 1 });
      }
    });
  });

  const categoryScores = allCategories.map((c) => ({
    name: c.name,
    score: c.score / c.count,
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium">Dataset Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <DatasetScoreChart data={datasetScores} title="" />
        </CardContent>
      </Card>

      {categoryScores.length >= 3 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">
              Category Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CategoryRadarChart data={categoryScores} title="" />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
