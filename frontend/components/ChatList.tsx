"use client";

import type { Chat } from "../lib/types";

interface Props {
  chats: Chat[];
  workspaceId: string;
}

export default function ChatList({ chats, workspaceId }: Props) {
  if (chats.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-sm text-gray-500">No chats yet</p>
        <p className="mt-1 text-xs text-gray-400">
          Start a new chat to work on your assignment with AI
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {chats.map((chat) => (
        <a
          key={chat.id}
          href={`/workspaces/${workspaceId}/chats/${chat.id}`}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 transition hover:border-indigo-300 hover:shadow-sm"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-gray-900 text-sm">{chat.title}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {chat.message_count} message{chat.message_count !== 1 ? "s" : ""}
            </p>
          </div>
          <span className="ml-3 text-xs text-gray-400">
            {new Date(chat.created_at).toLocaleDateString()}
          </span>
        </a>
      ))}
    </div>
  );
}
