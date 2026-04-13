"use client";

import type {
  Chat,
  ChatWithMessages,
  Message,
  ReportResponse,
  Submission,
  UploadedFile,
  Workspace,
} from "./types";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8888";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// Workspaces
export async function createWorkspace(title: string): Promise<Workspace> {
  return request("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function listWorkspaces(): Promise<{ workspaces: Workspace[] }> {
  return request("/api/workspaces");
}

export async function getWorkspace(id: string): Promise<Workspace> {
  return request(`/api/workspaces/${id}`);
}

export async function updateWorkspace(id: string, title: string): Promise<Workspace> {
  return request(`/api/workspaces/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function deleteWorkspace(id: string): Promise<void> {
  return request(`/api/workspaces/${id}`, { method: "DELETE" });
}

// Chats
export async function createChat(workspaceId: string, title?: string): Promise<Chat> {
  return request(`/api/workspaces/${workspaceId}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || null }),
  });
}

export async function listChats(workspaceId: string): Promise<{ chats: Chat[] }> {
  return request(`/api/workspaces/${workspaceId}/chats`);
}

export async function getChat(chatId: string): Promise<ChatWithMessages> {
  return request(`/api/chats/${chatId}`);
}

export async function updateChat(chatId: string, title: string): Promise<Chat> {
  return request(`/api/chats/${chatId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function deleteChat(chatId: string): Promise<void> {
  return request(`/api/chats/${chatId}`, { method: "DELETE" });
}

// Messages (streaming)
export async function sendMessageStream(
  chatId: string,
  content: string,
  callbacks: {
    onUserMessage: (msg: Message) => void;
    onDelta: (text: string) => void;
    onAssistantMessage: (msg: Message) => void;
    onError: (text: string) => void;
    onDone: () => void;
  },
): Promise<void> {
  const res = await fetch(`${API}/api/chats/${chatId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const raw = line.slice(6);
        try {
          const data = JSON.parse(raw);
          switch (currentEvent) {
            case "user_message":
              callbacks.onUserMessage(data as Message);
              break;
            case "delta":
              callbacks.onDelta(data.text);
              break;
            case "assistant_message":
              callbacks.onAssistantMessage(data as Message);
              break;
            case "error":
              callbacks.onError(data.text);
              break;
            case "done":
              callbacks.onDone();
              break;
          }
        } catch {
          // skip malformed data lines
        }
        currentEvent = "";
      }
    }
  }

  callbacks.onDone();
}

// Files
export async function uploadFile(workspaceId: string, file: File): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  return request(`/api/workspaces/${workspaceId}/files`, {
    method: "POST",
    body: form,
  });
}

export async function listFiles(workspaceId: string): Promise<{ files: UploadedFile[] }> {
  return request(`/api/workspaces/${workspaceId}/files`);
}

export async function updateFile(
  fileId: string,
  data: { file_role?: string; is_available_for_ai_context?: boolean },
): Promise<UploadedFile> {
  return request(`/api/files/${fileId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteFile(fileId: string): Promise<void> {
  return request(`/api/files/${fileId}`, { method: "DELETE" });
}

// Submissions
export async function submitWorkspace(
  workspaceId: string,
  primaryFileId: string,
  supportingFileIds: string[] = [],
): Promise<Submission> {
  return request(`/api/workspaces/${workspaceId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      primary_file_id: primaryFileId,
      supporting_file_ids: supportingFileIds,
    }),
  });
}

export async function getSubmission(workspaceId: string): Promise<Submission> {
  return request(`/api/workspaces/${workspaceId}/submission`);
}

// Reports
export async function getReport(workspaceId: string): Promise<ReportResponse> {
  return request(`/api/workspaces/${workspaceId}/report`);
}
