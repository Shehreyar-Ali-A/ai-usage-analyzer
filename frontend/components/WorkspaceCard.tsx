"use client";

import type { Workspace } from "../lib/types";

export default function WorkspaceCard({ workspace }: { workspace: Workspace }) {
  const isSubmitted = workspace.status === "submitted";
  const date = new Date(workspace.created_at).toLocaleDateString();

  return (
    <a
      href={`/workspaces/${workspace.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-5 transition hover:shadow-md hover:border-indigo-300"
    >
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-gray-900 truncate pr-2">{workspace.title}</h3>
        <span
          className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            isSubmitted
              ? "bg-green-100 text-green-800"
              : "bg-blue-100 text-blue-800"
          }`}
        >
          {isSubmitted ? "Submitted" : "Active"}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
        <span>{workspace.chat_count} chat{workspace.chat_count !== 1 ? "s" : ""}</span>
        <span>{workspace.file_count} file{workspace.file_count !== 1 ? "s" : ""}</span>
      </div>
      <div className="mt-2 text-xs text-gray-400">Created {date}</div>
    </a>
  );
}
