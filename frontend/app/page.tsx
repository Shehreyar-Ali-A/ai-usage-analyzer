"use client";

import { useState } from "react";

import type { AnalyzeResponse } from "../lib/api";
import { ReportView } from "../components/ReportView";
import { UploadForm } from "../components/UploadForm";

export default function HomePage() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  return (
    <main className="container">
      <div className="card">
        <h1 className="title">AI Usage Analyzer</h1>
        <p className="subtitle">
          Upload a student assignment and AI chat history to generate a transparent AI usage report.
        </p>

        <UploadForm onResult={setResult} />

        {result && (
          <ReportView
            report={result.report}
            markdown={result.markdown_report}
            pdfBase64={result.pdf_base64 ?? undefined}
          />
        )}
      </div>
    </main>
  );
}

