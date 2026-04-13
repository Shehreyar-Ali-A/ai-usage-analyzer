"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReport } from "../../../../lib/api";
import type { ReportResponse } from "../../../../lib/types";
import ReportView from "../../../../components/ReportView";

export default function ReportPage() {
  const params = useParams();
  const workspaceId = params.id as string;
  const [data, setData] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const report = await getReport(workspaceId);
        setData(report);
      } catch (e: any) {
        setError(e.message || "Failed to load report");
      } finally {
        setLoading(false);
      }
    };
    load();

    // Poll if still analyzing
    const interval = setInterval(async () => {
      try {
        const report = await getReport(workspaceId);
        setData(report);
        if (report.status === "completed" || report.status === "failed") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [workspaceId]);

  if (loading) {
    return <div className="py-12 text-center text-gray-500">Loading report...</div>;
  }

  if (error) {
    return <div className="py-12 text-center text-red-500">{error}</div>;
  }

  if (!data) {
    return <div className="py-12 text-center text-gray-500">No report found</div>;
  }

  return (
    <div>
      <a
        href={`/workspaces/${workspaceId}`}
        className="text-sm text-indigo-600 hover:text-indigo-800 mb-4 inline-block"
      >
        &larr; Back to Workspace
      </a>

      {(data.status === "pending" || data.status === "running") && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-6 text-center">
          <p className="text-blue-800 font-medium">Analysis in Progress</p>
          <p className="mt-1 text-sm text-blue-600">
            This may take a few minutes. The page will update automatically.
          </p>
        </div>
      )}

      {data.status === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-red-800 font-medium">Analysis Failed</p>
          <p className="mt-1 text-sm text-red-600">
            Something went wrong during analysis. Please contact support.
          </p>
        </div>
      )}

      {data.status === "completed" && data.report && (
        <ReportView report={data.report} markdown={data.markdown} />
      )}
    </div>
  );
}
