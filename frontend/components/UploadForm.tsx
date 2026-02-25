"use client";

import { useState } from "react";

import type { AnalyzeResponse } from "../lib/api";
import { analyzeAssignment } from "../lib/api";

type Props = {
  onResult: (result: AnalyzeResponse) => void;
};

export function UploadForm({ onResult }: Props) {
  const [assignmentFile, setAssignmentFile] = useState<File | null>(null);
  const [chatFile, setChatFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!assignmentFile || !chatFile) {
      setError("Please upload both an assignment file and a chat JSON file.");
      return;
    }

    const assignmentExt = assignmentFile.name.toLowerCase().split(".").pop();
    if (assignmentExt !== "pdf" && assignmentExt !== "docx") {
      setError("Assignment file must be a .pdf or .docx.");
      return;
    }

    const chatExt = chatFile.name.toLowerCase().split(".").pop();
    if (chatExt !== "json") {
      setError("Chat history file must be a .json file.");
      return;
    }

    try {
      setIsSubmitting(true);
      setStatus("Uploading and analyzing files...");
      const result = await analyzeAssignment({ assignmentFile, chatJsonFile: chatFile });
      onResult(result);
      setStatus("Analysis complete.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(message);
      setStatus(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="grid" onSubmit={handleSubmit}>
      <div className="input-group">
        <label className="input-label" htmlFor="assignment">
          Assignment file (.pdf or .docx)
        </label>
        <input
          id="assignment"
          type="file"
          className="input"
          accept=".pdf,.docx"
          onChange={(e) => setAssignmentFile(e.target.files?.[0] ?? null)}
        />
        <span className="input-helper">Max size: 10MB</span>
      </div>

      <div className="input-group">
        <label className="input-label" htmlFor="chat">
          AI chat history (.json)
        </label>
        <input
          id="chat"
          type="file"
          className="input"
          accept=".json"
          onChange={(e) => setChatFile(e.target.files?.[0] ?? null)}
        />
        <span className="input-helper">Exported JSON of the student&apos;s AI conversation.</span>
      </div>

      {status && <p className="status">{status}</p>}
      {error && <p className="error">{error}</p>}

      <button className="button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Generating Report..." : "Generate Report"}
      </button>
    </form>
  );
}

