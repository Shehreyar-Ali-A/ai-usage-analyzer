"use client";

import { useRef, useState } from "react";
import { uploadFile } from "../lib/api";

interface Props {
  workspaceId: string;
  onUpload: () => void;
}

export default function FileUploader({ workspaceId, onUpload }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError("");

    try {
      for (const file of Array.from(fileList)) {
        await uploadFile(workspaceId, file);
      }
      onUpload();
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="mb-3">
      <div
        className="flex cursor-pointer items-center justify-center rounded-lg border-2 border-dashed border-gray-300 px-4 py-4 transition hover:border-indigo-400 hover:bg-indigo-50/50"
        onClick={() => inputRef.current?.click()}
      >
        <div className="text-center">
          <p className="text-sm text-gray-600">
            {uploading ? "Uploading..." : "Click to upload files"}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">
            PDF, DOCX, TXT, images, or other assignment files
          </p>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}
