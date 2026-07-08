import { FormEvent, useState } from "react";
import "./PromptBar.css";

interface Props {
  onSubmit: (prompt: string) => Promise<void>;
  loading: boolean;
}

export default function PromptBar({ onSubmit, loading }: Props) {
  const [prompt, setPrompt] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    await onSubmit(prompt.trim());
    setPrompt("");
  }

  return (
    <div className="prompt-bar">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder='e.g. "Create an S3 bucket with public read access"'
          disabled={loading}
        />
        <button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? "Generating..." : "Generate Plan"}
        </button>
      </form>
      <p className="hint">
        Try: public S3 bucket, open security group, or private storage bucket
      </p>
    </div>
  );
}
