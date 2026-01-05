import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!prompt.trim()) {
      return;
    }

    setLoading(true);
    setError("");
    setResponse("");

    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "Request failed");
      }

      const data = await res.json();
      setResponse(data.response || "No response returned.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <h1>Ollama Chat</h1>
        <p>Send a prompt to the Ollama container using the FastAPI gateway.</p>
      </header>

      <main className="card">
        <form onSubmit={handleSubmit}>
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Ask something..."
            rows={6}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Generating..." : "Send"}
          </button>
        </form>

        <section className="output">
          <h2>Response</h2>
          {error ? (
            <p className="error">{error}</p>
          ) : (
            <pre>{response || "Your response will appear here."}</pre>
          )}
        </section>
      </main>
    </div>
  );
}
