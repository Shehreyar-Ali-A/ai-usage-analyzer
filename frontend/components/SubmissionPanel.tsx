"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { submitWorkspace, getSubmission } from "../lib/api";
import type { Submission, UploadedFile, Workspace } from "../lib/types";

interface Props {
  workspace: Workspace;
  files: UploadedFile[];
  submission: Submission | null;
  onSubmit: () => void;
}

export default function SubmissionPanel({ workspace, files, submission: initialSubmission, onSubmit }: Props) {
  const router = useRouter();
  const [primaryFileId, setPrimaryFileId] = useState("");
  const [supportingIds, setSupportingIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [submission, setSubmission] = useState<Submission | null>(initialSubmission);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setSubmission(initialSubmission);
  }, [initialSubmission]);

  // Poll for status updates while analyzing
  useEffect(() => {
    const shouldPoll = submission &&
      (submission.status === "submitted" || submission.status === "analyzing");

    if (!shouldPoll) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const updated = await getSubmission(workspace.id);
        setSubmission(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // ignore polling errors
      }
    }, 3000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [submission?.status, workspace.id]);

  if (submission) {
    const primaryFile = files.find((f) => f.id === submission.primary_file_id);
    const isAnalyzing = submission.status === "submitted" || submission.status === "analyzing";

    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-white text-xs">
            &#10003;
          </span>
          <h3 className="font-semibold text-green-900">Workspace Submitted</h3>
        </div>
        <p className="text-sm text-green-800">
          Primary file: {primaryFile?.original_filename || "Unknown"}
        </p>
        <p className="text-sm text-green-800">
          Status: <span className="font-medium capitalize">{submission.status}</span>
        </p>

        {isAnalyzing && (
          <div className="mt-3 flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-green-600 border-t-transparent" />
            <p className="text-sm text-green-700">
              Analysis in progress... This may take a minute.
            </p>
          </div>
        )}

        {submission.status === "completed" && (
          <button
            onClick={() => router.push(`/workspaces/${workspace.id}/report`)}
            className="mt-3 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            View Analysis Report
          </button>
        )}

        {submission.status === "failed" && (
          <p className="mt-2 text-sm text-red-600">
            Analysis failed. Please try creating a new workspace and re-submitting.
          </p>
        )}
      </div>
    );
  }

  if (workspace.status === "submitted") {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
        Workspace has been submitted.
      </div>
    );
  }

  const allFiles = files;

  const toggleSupporting = (id: string) => {
    setSupportingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const handleSubmit = async () => {
    if (!primaryFileId) {
      setError("Please select a primary submission file");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const sub = await submitWorkspace(
        workspace.id,
        primaryFileId,
        supportingIds.filter((id) => id !== primaryFileId),
      );
      setSubmission(sub);
      onSubmit();
    } catch (e: any) {
      setError(e.message || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (files.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
        Upload files before submitting your workspace.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="mb-3 text-sm text-gray-600">
        Select your final submission file and any supporting files, then submit.
        This action is final and will lock the workspace.
      </p>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Primary Submission File
        </label>
        <select
          value={primaryFileId}
          onChange={(e) => setPrimaryFileId(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
        >
          <option value="">Select a file...</option>
          {allFiles.map((f) => (
            <option key={f.id} value={f.id}>
              {f.original_filename}
            </option>
          ))}
        </select>
      </div>

      {allFiles.filter((f) => f.id !== primaryFileId).length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Supporting Files (optional)
          </label>
          <div className="space-y-1">
            {allFiles
              .filter((f) => f.id !== primaryFileId)
              .map((f) => (
                <label key={f.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={supportingIds.includes(f.id)}
                    onChange={() => toggleSupporting(f.id)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-gray-700">{f.original_filename}</span>
                </label>
              ))}
          </div>
        </div>
      )}

      {error && <p className="mb-3 text-sm text-red-500">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={submitting || !primaryFileId}
        className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting ? "Submitting..." : "Submit Workspace"}
      </button>
    </div>
  );
}
