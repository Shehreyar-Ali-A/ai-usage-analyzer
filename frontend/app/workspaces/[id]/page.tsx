"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getWorkspace,
  updateWorkspace,
  createChat,
  listChats,
  listFiles,
  getSubmission,
} from "../../../lib/api";
import type { Chat, Workspace, UploadedFile, Submission } from "../../../lib/types";
import ChatList from "../../../components/ChatList";
import FileList from "../../../components/FileList";
import FileUploader from "../../../components/FileUploader";
import SubmissionPanel from "../../../components/SubmissionPanel";

export default function WorkspaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");

  const loadAll = async () => {
    try {
      const [ws, chatData, fileData] = await Promise.all([
        getWorkspace(workspaceId),
        listChats(workspaceId),
        listFiles(workspaceId),
      ]);
      setWorkspace(ws);
      setChats(chatData.chats);
      setFiles(fileData.files);
      setTitleDraft(ws.title);

      try {
        const sub = await getSubmission(workspaceId);
        setSubmission(sub);
      } catch {
        setSubmission(null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [workspaceId]);

  const handleTitleSave = async () => {
    if (!titleDraft.trim() || titleDraft === workspace?.title) {
      setEditingTitle(false);
      return;
    }
    try {
      const updated = await updateWorkspace(workspaceId, titleDraft.trim());
      setWorkspace(updated);
      setEditingTitle(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewChat = async () => {
    try {
      const chat = await createChat(workspaceId);
      router.push(`/workspaces/${workspaceId}/chats/${chat.id}`);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return <div className="py-12 text-center text-gray-500">Loading workspace...</div>;
  }

  if (!workspace) {
    return <div className="py-12 text-center text-gray-500">Workspace not found</div>;
  }

  const isSubmitted = workspace.status === "submitted";

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <a href="/workspaces" className="text-sm text-indigo-600 hover:text-indigo-800 mb-2 inline-block">
          &larr; Back to Workspaces
        </a>
        <div className="flex items-center gap-3">
          {editingTitle ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xl font-bold focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleTitleSave();
                  if (e.key === "Escape") setEditingTitle(false);
                }}
                autoFocus
              />
              <button onClick={handleTitleSave} className="text-sm text-indigo-600 hover:text-indigo-800">
                Save
              </button>
            </div>
          ) : (
            <h1
              className="text-2xl font-bold text-gray-900 cursor-pointer hover:text-indigo-600"
              onClick={() => !isSubmitted && setEditingTitle(true)}
              title={isSubmitted ? "" : "Click to edit title"}
            >
              {workspace.title}
            </h1>
          )}
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              isSubmitted ? "bg-green-100 text-green-800" : "bg-blue-100 text-blue-800"
            }`}
          >
            {isSubmitted ? "Submitted" : "Active"}
          </span>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Left: Chats */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Chats</h2>
            {!isSubmitted && (
              <button
                onClick={handleNewChat}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
              >
                New Chat
              </button>
            )}
          </div>
          <ChatList chats={chats} workspaceId={workspaceId} />
        </div>

        {/* Right: Files + Submission */}
        <div className="space-y-8">
          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Files</h2>
            {!isSubmitted && (
              <FileUploader workspaceId={workspaceId} onUpload={loadAll} />
            )}
            <FileList files={files} onUpdate={loadAll} isSubmitted={isSubmitted} />
          </div>

          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Submission</h2>
            <SubmissionPanel
              workspace={workspace}
              files={files}
              submission={submission}
              onSubmit={loadAll}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
