import Link from "next/link";
import { getSamples, getRunMeta } from "@/lib/api";
import { SamplesPageClient } from "@/components/SamplesPageClient";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ dataset?: string }>;
}

export default async function SamplesPage({ params, searchParams }: PageProps) {
  const { runId } = await params;
  const { dataset } = await searchParams;

  let meta;
  let samples;
  let error = null;

  try {
    meta = await getRunMeta(runId);

    if (!dataset) {
      error = "No dataset specified";
    } else {
      samples = await getSamples(runId, dataset);
    }
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load samples";
  }

  if (error || !meta || !samples) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            Error Loading Samples
          </h2>
          <p className="text-red-700">{error}</p>
          <Link
            href={`/runs/${runId}`}
            className="text-blue-600 hover:underline mt-4 inline-block"
          >
            Back to run details
          </Link>
        </div>
      </div>
    );
  }

  return (
    <SamplesPageClient
      runId={runId}
      dataset={dataset!}
      datasets={meta.datasets}
      samples={samples}
      modelName={meta.model.name}
    />
  );
}
