import Link from "next/link";
import { getRunData } from "@/lib/api";
import { formatDate, formatDuration, formatScore } from "@/lib/utils";
import { BenchmarkResultsTable } from "@/components/BenchmarkResultsTable";
import { RunChartsSection } from "@/components/RunChartsSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ runId: string }>;
}

export default async function RunDetailPage({ params }: PageProps) {
  const { runId } = await params;

  let data;
  let error = null;

  try {
    data = await getRunData(runId);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load run data";
  }

  if (error || !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            Error Loading Run
          </h2>
          <p className="text-red-700">{error}</p>
          <Link
            href="/"
            className="text-blue-600 hover:underline mt-4 inline-block"
          >
            Back to runs
          </Link>
        </div>
      </div>
    );
  }

  const { meta, summary } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back button */}
      <div className="mb-4">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-gray-600 hover:text-gray-900 hover:bg-gray-100">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to runs
          </Button>
        </Link>
      </div>

      {/* Header Card */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">
                {meta.model.name}
              </h1>
              <p className="text-sm text-gray-500">{runId}</p>
            </div>
            <Badge
              variant={
                meta.status === "completed"
                  ? "success"
                  : meta.status === "failed"
                    ? "destructive"
                    : "warning"
              }
              className="text-sm"
            >
              {meta.status}
            </Badge>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">Framework</p>
              <p className="text-lg font-semibold text-gray-900">
                {meta.environment?.framework || "evalscope"}{" "}
                {meta.environment?.framework_version || ""}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Evaluation Type</p>
              <p className="text-lg font-semibold text-gray-900">
                {meta.model.type}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Overall Score</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatScore(summary.overall.avg_score)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Total Samples</p>
              <p className="text-lg font-semibold text-gray-900">
                {summary.overall.total_samples.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Run Information */}
          <div className="border-t border-gray-100 pt-6">
            <h3 className="text-sm font-medium text-gray-900 mb-3">
              Run Information
            </h3>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <dt className="text-gray-500">Start Time</dt>
                <dd className="font-medium text-gray-900">
                  {formatDate(meta.start_time)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">End Time</dt>
                <dd className="font-medium text-gray-900">
                  {formatDate(meta.end_time)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Duration</dt>
                <dd className="font-medium text-gray-900">
                  {formatDuration(meta.duration_seconds)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Model Revision</dt>
                <dd className="font-medium text-gray-900">
                  {meta.model.revision || "N/A"}
                </dd>
              </div>
            </dl>
          </div>

          {/* Configuration */}
          {meta.config &&
            (meta.config.eval_batch_size || meta.config.seed !== undefined) && (
              <div className="border-t border-gray-100 pt-6 mt-6">
                <h3 className="text-sm font-medium text-gray-900 mb-3">
                  Configuration
                </h3>
                <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {meta.config.eval_batch_size && (
                    <div>
                      <dt className="text-gray-500">Batch Size</dt>
                      <dd className="font-medium text-gray-900">
                        {meta.config.eval_batch_size}
                      </dd>
                    </div>
                  )}
                  {meta.config.seed !== null && meta.config.seed !== undefined && (
                    <div>
                      <dt className="text-gray-500">Seed</dt>
                      <dd className="font-medium text-gray-900">
                        {meta.config.seed}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            )}
        </CardContent>
      </Card>

      {/* Charts Section */}
      <RunChartsSection datasets={summary.datasets} />

      {/* Benchmark Results Table */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Evaluation Results</CardTitle>
        </CardHeader>
        <CardContent>
          <BenchmarkResultsTable results={summary.datasets} />
        </CardContent>
      </Card>

      {/* Sample Predictions Links */}
      <Card>
        <CardHeader>
          <CardTitle>Sample Predictions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 mb-4">
            View detailed sample predictions for each dataset
          </p>
          <div className="flex flex-wrap gap-3">
            {meta.datasets.map((dataset) => (
              <Button key={dataset} variant="outline" asChild>
                <Link href={`/runs/${runId}/samples?dataset=${dataset}`}>
                  View {dataset} samples
                </Link>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
