import { FormEvent, useEffect, useMemo, useState } from "react";

type HermesResult = {
  ok?: boolean;
  status?: string;
  intent?: string;
  reply_text?: string;
  display_text?: string;
  turn_id?: string;
  linked_job_id?: string;
  error?: string;
  detail?: string;
  [key: string]: unknown;
};

const TOKEN_KEY = "hermes_remote_dashboard_token";
const DEFAULT_DEVICE_ID = "m5stick-s3-pet-01";
const DEFAULT_SESSION_ID = "main-session";

async function callHermes(path: string, token: string, init: RequestInit = {}): Promise<HermesResult> {
  const response = await fetch(`/api/hermes${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Remote-Dashboard-Token": token,
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  let payload: HermesResult;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: text || response.statusText };
  }
  if (!response.ok) {
    throw new Error(payload.error || payload.detail || `${response.status} ${response.statusText}`);
  }
  return payload;
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [deviceId, setDeviceId] = useState(DEFAULT_DEVICE_ID);
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION_ID);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<HermesResult | null>(null);
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant" | "system"; text: string }>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  }, [token]);

  const canSend = useMemo(() => token.trim() && text.trim() && !busy, [busy, text, token]);

  async function checkHealth() {
    setBusy(true);
    setError("");
    try {
      const payload = await callHermes("/healthz", token.trim());
      setHealth(payload);
      setMessages((items) => [...items, { role: "system", text: "Hermes local agent is reachable." }]);
    } catch (err) {
      setHealth(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!canSend) return;
    const userText = text.trim();
    setText("");
    setBusy(true);
    setError("");
    setMessages((items) => [...items, { role: "user", text: userText }]);
    try {
      const payload = await callHermes("/api/companion/text-turns", token.trim(), {
        method: "POST",
        body: JSON.stringify({
          device_id: deviceId.trim() || DEFAULT_DEVICE_ID,
          session_id: sessionId.trim() || DEFAULT_SESSION_ID,
          text: userText,
          attachments: [],
        }),
      });
      const reply = payload.reply_text || payload.display_text || JSON.stringify(payload, null, 2);
      setMessages((items) => [...items, { role: "assistant", text: String(reply) }]);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setError(detail);
      setMessages((items) => [...items, { role: "system", text: `Send failed: ${detail}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Hermes Remote</p>
          <h1>Vercel to Local Agent</h1>
          <p className="lede">
            A thin remote control surface for the local Hermes worker. Vercel handles the UI and protected proxy;
            Cloudflare Tunnel carries the request home.
          </p>
        </div>
        <div className={`status ${health?.ok ? "online" : "offline"}`}>
          <span>{health?.ok ? "ONLINE" : "LOCKED"}</span>
          <small>{health?.ok ? "Local Hermes reachable" : "Enter token and check health"}</small>
        </div>
      </section>

      <section className="panel grid">
        <label>
          Remote token
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            type="password"
            placeholder="REMOTE_DASHBOARD_TOKEN"
            autoComplete="current-password"
          />
        </label>
        <label>
          Device
          <input value={deviceId} onChange={(event) => setDeviceId(event.target.value)} />
        </label>
        <label>
          Session
          <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
        </label>
        <button className="secondary" disabled={!token || busy} onClick={() => void checkHealth()}>
          {busy ? "Working..." : "Check Health"}
        </button>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="chat panel">
        <div className="messages">
          {messages.length === 0 ? (
            <div className="empty">
              <strong>No remote messages yet.</strong>
              <span>Start with a health check, then send a short command to M5S3 companion.</span>
            </div>
          ) : (
            messages.map((message, index) => (
              <article className={`bubble ${message.role}`} key={`${message.role}-${index}`}>
                <span>{message.role}</span>
                <p>{message.text}</p>
              </article>
            ))
          )}
        </div>

        <form className="composer" onSubmit={sendMessage}>
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Send a message to local Hermes / M5S3..."
            rows={3}
          />
          <button disabled={!canSend}>{busy ? "Sending..." : "Send"}</button>
        </form>
      </section>
    </main>
  );
}
