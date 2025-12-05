import { getRunsIndex } from "@/lib/api";
import { RunsPageClient } from "@/components/RunsPageClient";

export const dynamic = "force-dynamic";

export default async function Home() {
  let runsIndex;
  let error = null;

  try {
    runsIndex = await getRunsIndex();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load runs";
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">
            Connection Error
          </h2>
          <p className="text-yellow-700 mb-4">{error}</p>
          <p className="text-yellow-600 text-sm">
            Make sure the backend server is running at{" "}
            <code className="bg-yellow-100 px-1 rounded">
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:7862"}
            </code>
          </p>
        </div>
      </div>
    );
  }

  const runs = runsIndex?.runs || [];

  return (
    <RunsPageClient runs={runs} lastUpdated={runsIndex?.last_updated} />
  );
}
