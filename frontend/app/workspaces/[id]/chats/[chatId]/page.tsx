"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getChat, sendMessageStream, updateChat, getWorkspace } from "../../../../../lib/api";
import type { ChatWithMessages, Message, Workspace } from "../../../../../lib/types";
import MessageBubble from "../../../../../components/MessageBubble";

export default function ChatPage() {
  const params = useParams();
  const workspaceId = params.id as string;
  const chatId = params.chatId as string;

  const [chat, setChat] = useState<ChatWithMessages | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadChat = async () => {
    try {
      const [chatData, ws] = await Promise.all([
        getChat(chatId),
        getWorkspace(workspaceId),
      ]);
      setChat(chatData);
      setWorkspace(ws);
      setMessages(chatData.messages);
      setTitleDraft(chatData.title);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadChat();
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;
    const content = input.trim();
    setInput("");
    setSending(true);
    setStreamingText("");

    try {
      await sendMessageStream(chatId, content, {
        onUserMessage(msg) {
          setMessages((prev) => {
            const filtered = prev.filter((m) => !m.id.startsWith("temp-"));
            return [...filtered, msg];
          });
        },
        onDelta(text) {
          setStreamingText((prev) => prev + text);
        },
        onAssistantMessage(msg) {
          setStreamingText("");
          setMessages((prev) => [...prev, msg]);
        },
        onError(text) {
          setStreamingText("");
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              chat_id: chatId,
              role: "assistant",
              content_text: `Error: ${text}`,
              sequence_number: prev.length + 1,
              openai_response_id: null,
              metadata_jsonb: null,
              created_at: new Date().toISOString(),
            },
          ]);
        },
        onDone() {},
      });
    } catch (e: any) {
      setStreamingText("");
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          chat_id: chatId,
          role: "assistant",
          content_text: `Error: ${e.message || "Failed to send message"}`,
          sequence_number: prev.length + 1,
          openai_response_id: null,
          metadata_jsonb: null,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
      setStreamingText("");
    }
  }, [input, sending, chatId]);

  const handleTitleSave = async () => {
    if (!titleDraft.trim() || titleDraft === chat?.title) {
      setEditingTitle(false);
      return;
    }
    try {
      await updateChat(chatId, titleDraft.trim());
      setChat((prev) => prev ? { ...prev, title: titleDraft.trim() } : prev);
      setEditingTitle(false);
    } catch (e) {
      console.error(e);
    }
  };

  const isSubmitted = workspace?.status === "submitted";

  if (!chat) {
    return <div className="py-12 text-center text-gray-500">Loading chat...</div>;
  }

  return (
    <div className="flex h-[calc(100vh-130px)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4 mb-4">
        <div className="flex items-center gap-3">
          <a
            href={`/workspaces/${workspaceId}`}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            &larr; Workspace
          </a>
          <span className="text-gray-300">|</span>
          {editingTitle ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                className="rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleTitleSave();
                  if (e.key === "Escape") setEditingTitle(false);
                }}
                autoFocus
              />
              <button onClick={handleTitleSave} className="text-xs text-indigo-600">
                Save
              </button>
            </div>
          ) : (
            <h2
              className="font-semibold text-gray-900 cursor-pointer hover:text-indigo-600 text-sm"
              onClick={() => !isSubmitted && setEditingTitle(true)}
            >
              {chat.title}
            </h2>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && !streamingText && (
          <div className="py-16 text-center">
            <p className="text-gray-500">Start a conversation about your assignment</p>
            <p className="mt-1 text-sm text-gray-400">
              The AI can help you brainstorm, explain concepts, review your work, and more.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl bg-gray-100 px-4 py-3 text-sm leading-relaxed text-gray-900">
              <div className="whitespace-pre-wrap break-words">
                {streamingText}
                <span className="inline-block w-1.5 h-4 ml-0.5 bg-indigo-500 animate-pulse rounded-sm align-text-bottom" />
              </div>
            </div>
          </div>
        )}
        {sending && !streamingText && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500 italic">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      {!isSubmitted && (
        <div className="border-t border-gray-200 pt-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              disabled={sending}
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      )}
      {isSubmitted && (
        <div className="border-t border-gray-200 pt-4 text-center text-sm text-gray-500">
          This workspace has been submitted. Chat is read-only.
        </div>
      )}
    </div>
  );
}
