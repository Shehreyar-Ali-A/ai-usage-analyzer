"use client";

import { useState } from "react";
import { updateFile, deleteFile } from "../lib/api";
import type { UploadedFile } from "../lib/types";

const FILE_ROLES = [
  { value: "context", label: "Context / Reference" },
  { value: "supplementary", label: "Supplementary" },
  { value: "final_submission_primary", label: "Final Submission (Primary)" },
  { value: "final_submission_supporting", label: "Final Submission (Supporting)" },
];

interface Props {
  files: UploadedFile[];
  onUpdate: () => void;
  isSubmitted: boolean;
}

export default function FileList({ files, onUpdate, isSubmitted }: Props) {
  const [updating, setUpdating] = useState<string | null>(null);

  if (files.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center mt-3">
        <p className="text-sm text-gray-500">No files uploaded</p>
      </div>
    );
  }

  const handleRoleChange = async (fileId: string, newRole: string) => {
    setUpdating(fileId);
    try {
      await updateFile(fileId, { file_role: newRole });
      onUpdate();
    } catch (e) {
      console.error(e);
    } finally {
      setUpdating(null);
    }
  };

  const handleDelete = async (fileId: string) => {
    if (!confirm("Remove this file?")) return;
    try {
      await deleteFile(fileId);
      onUpdate();
    } catch (e) {
      console.error(e);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="mt-3 space-y-2">
      {files.map((f) => (
        <div
          key={f.id}
          className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-900">
              {f.original_filename}
            </p>
            <p className="text-xs text-gray-400">
              {formatSize(f.file_size_bytes)} &middot; {f.mime_type}
              {f.is_available_for_ai_context && (
                <span className="ml-2 text-indigo-500">AI context</span>
              )}
            </p>
          </div>

          {!isSubmitted && (
            <>
              <select
                value={f.file_role}
                onChange={(e) => handleRoleChange(f.id, e.target.value)}
                disabled={updating === f.id}
                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 focus:border-indigo-500 focus:outline-none"
              >
                {FILE_ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handleDelete(f.id)}
                className="text-xs text-red-500 hover:text-red-700"
              >
                Remove
              </button>
            </>
          )}

          {isSubmitted && (
            <span className="text-xs text-gray-500">
              {FILE_ROLES.find((r) => r.value === f.file_role)?.label || f.file_role}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
