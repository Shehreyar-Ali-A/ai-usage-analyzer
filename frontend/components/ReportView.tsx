import type { AnalyzeReport } from "../lib/api";

type Props = {
  report: AnalyzeReport;
  markdown: string;
  pdfBase64?: string | null;
};

function relationLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ReportView({ report, markdown, pdfBase64 }: Props) {
  const handleDownloadMarkdown = () => {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ai-usage-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = () => {
    if (!pdfBase64) return;
    const byteCharacters = atob(pdfBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i += 1) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ai-usage-report.pdf";
    a.click();
    URL.revokeObjectURL(url);
  };

  const factors = report.factor_breakdown ?? [];
  const increasing = report.increasing_factors ?? [];
  const decreasing = report.decreasing_factors ?? [];
  const transformations = report.transformation_findings ?? [];
  const caveats = report.caveats ?? [];

  return (
    <div className="section">
      <div className="section-title">AI Usage Summary</div>
      <p>{report.summary}</p>

      <div className="section">
        <div className="section-title">Reliance Score</div>
        <div className="badge">
          Score {report.reliance_score} &middot; {report.reliance_label}
        </div>
        <div className="score-bar" aria-hidden="true">
          <div
            className="score-bar-inner"
            style={{
              width: `${report.reliance_score}%`
            }}
          />
        </div>
      </div>

      {factors.length > 0 && (
        <div className="section">
          <div className="section-title">Factor Breakdown</div>
          <div className="factor-table">
            {factors.map((f) => (
              <div key={f.name} className="factor-row">
                <div className="factor-name">{f.name}</div>
                <div className="factor-bar-container">
                  <div
                    className="factor-bar"
                    style={{ width: `${Math.round(f.score * 100)}%` }}
                  />
                </div>
                <div className="factor-score">{Math.round(f.score * 100)}%</div>
                <div className="factor-weight">({Math.round(f.weight * 100)}% weight)</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.prompt_intent_summary && (
        <div className="section">
          <div className="section-title">Prompt Intent</div>
          <p>{report.prompt_intent_summary}</p>
        </div>
      )}

      <div className="section">
        <div className="section-title">AI Usage Classification</div>
        <div className="chips">
          {report.usage_type.length === 0 && <span className="chip">Not clearly classified</span>}
          {report.usage_type.map((type) => (
            <span key={type} className="chip">
              {type}
            </span>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-title">Evidence Matches</div>
        {report.evidence.length === 0 && <p className="status">No strong similarity matches detected.</p>}
        {report.evidence.map((ev, idx) => (
          <div key={idx} className="evidence-item">
            <div className="badge">Match {idx + 1}</div>
            <p className="status">
              Similarity: {Math.round(ev.similarity * 100)}%
              {ev.semantic_score != null && ev.lexical_score != null && (
                <span className="score-detail">
                  {" "}(semantic {Math.round(ev.semantic_score * 100)}%, lexical {Math.round(ev.lexical_score * 100)}%)
                </span>
              )}
            </p>
            {ev.relation_type && (
              <div className="chip relation-chip">{relationLabel(ev.relation_type)}</div>
            )}
            <div className="evidence-label">Assignment Excerpt</div>
            <p className="evidence-text">{ev.assignment_excerpt}</p>
            <div className="evidence-label">AI Excerpt</div>
            <p className="evidence-text">{ev.ai_excerpt}</p>
          </div>
        ))}
      </div>

      {transformations.length > 0 && (
        <div className="section">
          <div className="section-title">Transformation Findings</div>
          <ul>
            {transformations.map((t, idx) => (
              <li key={idx}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {(increasing.length > 0 || decreasing.length > 0) && (
        <div className="section">
          <div className="section-title">Score Factors</div>
          {increasing.length > 0 && (
            <>
              <div className="evidence-label">Factors increasing score</div>
              <ul>
                {increasing.map((f, idx) => (
                  <li key={`inc-${idx}`}>{f}</li>
                ))}
              </ul>
            </>
          )}
          {decreasing.length > 0 && (
            <>
              <div className="evidence-label">Factors decreasing score</div>
              <ul>
                {decreasing.map((f, idx) => (
                  <li key={`dec-${idx}`}>{f}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="section">
        <div className="section-title">Observations</div>
        <ul>
          {report.observations.map((obs, idx) => (
            <li key={idx}>{obs}</li>
          ))}
        </ul>
      </div>

      <div className="section">
        <div className="section-title">Confidence Level</div>
        <div className="badge">{report.confidence}</div>
        {caveats.length > 0 && (
          <ul className="caveats">
            {caveats.map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="section">
        <div className="section-title">Download Report</div>
        <div className="downloads">
          <button type="button" className="download-button" onClick={handleDownloadMarkdown}>
            Download Markdown
          </button>
          <button
            type="button"
            className="download-button"
            onClick={handleDownloadPdf}
            disabled={!pdfBase64}
          >
            Download PDF
          </button>
        </div>
      </div>
    </div>
  );
}
