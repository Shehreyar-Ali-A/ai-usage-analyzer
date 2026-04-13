"use client";

import type { AnalysisReport } from "../lib/types";

interface Props {
  report: AnalysisReport;
  markdown: string | null;
}

export default function ReportView({ report, markdown }: Props) {
  const scoreColor =
    report.reliance_label === "High"
      ? "text-red-600"
      : report.reliance_label === "Moderate"
        ? "text-yellow-600"
        : "text-green-600";

  const scoreBg =
    report.reliance_label === "High"
      ? "bg-red-50 border-red-200"
      : report.reliance_label === "Moderate"
        ? "bg-yellow-50 border-yellow-200"
        : "bg-green-50 border-green-200";

  const downloadMarkdown = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "analysis-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">AI Usage Analysis Report</h1>

      {/* Score Card */}
      <div className={`rounded-lg border p-6 ${scoreBg}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">AI Reliance Score</p>
            <p className={`text-4xl font-bold ${scoreColor}`}>
              {report.reliance_score}
              <span className="text-lg text-gray-500"> / 100</span>
            </p>
          </div>
          <div className="text-right">
            <span
              className={`inline-block rounded-full px-4 py-1.5 text-sm font-semibold ${scoreColor} ${scoreBg}`}
            >
              {report.reliance_label} Reliance
            </span>
            <p className="mt-1 text-xs text-gray-500">
              Confidence: {report.confidence}
            </p>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Summary</h2>
        <p className="text-sm text-gray-700 leading-relaxed">{report.summary}</p>
      </div>

      {/* Factor Breakdown */}
      {report.factor_breakdown.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Factor Breakdown</h2>
          <div className="space-y-3">
            {report.factor_breakdown.map((f, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="w-48 text-sm font-medium text-gray-700">{f.name}</div>
                <div className="flex-1">
                  <div className="h-2 rounded-full bg-gray-200">
                    <div
                      className="h-2 rounded-full bg-indigo-500"
                      style={{ width: `${Math.round(f.score * 100)}%` }}
                    />
                  </div>
                </div>
                <div className="w-12 text-right text-sm text-gray-600">
                  {(f.score * 100).toFixed(0)}%
                </div>
                <div className="w-14 text-right text-xs text-gray-400">
                  ({(f.weight * 100).toFixed(0)}% wt)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prompt Intent */}
      {report.prompt_intent_summary && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Prompt Intent</h2>
          <p className="text-sm text-gray-700">{report.prompt_intent_summary}</p>
        </div>
      )}

      {/* Usage Types */}
      {report.usage_type.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">AI Usage Types</h2>
          <div className="flex flex-wrap gap-2">
            {report.usage_type.map((t, i) => (
              <span
                key={i}
                className="rounded-full bg-indigo-100 px-3 py-1 text-sm text-indigo-800"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Evidence */}
      {report.evidence.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">
            Evidence Matches ({report.evidence.length})
          </h2>
          <div className="space-y-4">
            {report.evidence.map((ev, i) => (
              <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <div className="mb-2 flex items-center gap-3 text-xs text-gray-500">
                  <span>
                    Similarity: {Math.round(ev.similarity * 100)}% (semantic{" "}
                    {ev.semantic_score.toFixed(2)}, lexical {ev.lexical_score.toFixed(2)})
                  </span>
                  {ev.relation_type && (
                    <span className="rounded bg-gray-200 px-2 py-0.5">
                      {ev.relation_type.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="mb-1 text-xs font-medium text-gray-500">Assignment Excerpt</p>
                    <p className="text-sm text-gray-700 line-clamp-4">
                      {ev.assignment_excerpt}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-gray-500">AI Excerpt</p>
                    <p className="text-sm text-gray-700 line-clamp-4">{ev.ai_excerpt}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transformation Findings */}
      {report.transformation_findings.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">
            Transformation Findings
          </h2>
          <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
            {report.transformation_findings.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Increasing / Decreasing Factors */}
      <div className="grid gap-4 md:grid-cols-2">
        {report.increasing_factors.length > 0 && (
          <div className="rounded-lg border border-red-100 bg-red-50/50 p-5">
            <h3 className="mb-2 text-sm font-semibold text-red-800">
              Factors Increasing Score
            </h3>
            <ul className="list-disc pl-5 space-y-1 text-sm text-red-700">
              {report.increasing_factors.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
        )}
        {report.decreasing_factors.length > 0 && (
          <div className="rounded-lg border border-green-100 bg-green-50/50 p-5">
            <h3 className="mb-2 text-sm font-semibold text-green-800">
              Factors Decreasing Score
            </h3>
            <ul className="list-disc pl-5 space-y-1 text-sm text-green-700">
              {report.decreasing_factors.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Observations */}
      {report.observations.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Observations</h2>
          <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
            {report.observations.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Caveats */}
      {report.caveats.length > 0 && (
        <div className="rounded-lg border border-yellow-100 bg-yellow-50/50 p-5">
          <h2 className="mb-2 text-sm font-semibold text-yellow-800">Caveats</h2>
          <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-700">
            {report.caveats.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Download */}
      {markdown && (
        <div className="flex gap-3">
          <button
            onClick={downloadMarkdown}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Download Markdown Report
          </button>
        </div>
      )}
    </div>
  );
}
