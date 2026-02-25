import type { AnalyzeReport } from "../lib/api";

type Props = {
  report: AnalyzeReport;
  markdown: string;
  pdfBase64?: string | null;
};

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

  return (
    <div className="section">
      <div className="section-title">AI Usage Summary</div>
      <p>{report.summary}</p>

      <div className="section">
        <div className="section-title">Reliance Score</div>
        <div className="badge">
          Score {report.reliance_score} · {report.reliance_label}
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
            <p className="status">Similarity: {Math.round(ev.similarity * 100)}%</p>
            <div className="evidence-label">Assignment Excerpt</div>
            <p className="evidence-text">{ev.assignment_excerpt}</p>
            <div className="evidence-label">AI Excerpt</div>
            <p className="evidence-text">{ev.ai_excerpt}</p>
          </div>
        ))}
      </div>

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

