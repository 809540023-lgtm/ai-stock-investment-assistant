import { useState } from "react";
import { api } from "../api";

const SUGGESTIONS = [
  "現在這個價位適合進場嗎？",
  "這檔的主要風險是什麼？",
  "和同業相比有什麼優勢？",
  "如果跌 20% 我該加碼還是停損？",
];

type QA = { q: string; a: string };

export default function AskAI({ planId }: { planId: number }) {
  const [q, setQ] = useState("");
  const [history, setHistory] = useState<QA[]>([]);
  const [busy, setBusy] = useState(false);

  const ask = async (question: string) => {
    if (!question.trim() || busy) return;
    setBusy(true);
    setQ("");
    try {
      const r = await api.askPlan(planId, question);
      setHistory((h) => [...h, { q: question, a: r.answer }]);
    } catch (e) {
      setHistory((h) => [...h, { q: question, a: "（發生錯誤，請稍後再試）" }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ borderColor: "var(--accent)" }}>
      <div className="section-title">💬 AI 智能追問</div>
      <p className="muted" style={{ marginTop: -6 }}>針對這檔股票，問 AI 任何投資相關問題。</p>

      {history.map((qa, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>你：{qa.q}</div>
          <pre className="analysis" style={{ margin: 0 }}>{qa.a}</pre>
        </div>
      ))}

      {history.length === 0 && (
        <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="ghost small" onClick={() => ask(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="row" style={{ gap: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(q)}
          placeholder="輸入你的問題…"
          style={{ flex: 1 }}
        />
        <button onClick={() => ask(q)} disabled={busy || !q.trim()}>
          {busy ? "思考中…" : "送出"}
        </button>
      </div>
    </div>
  );
}
