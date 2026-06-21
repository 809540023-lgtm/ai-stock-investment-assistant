import { useEffect, useState } from "react";
import { api, HealthScore } from "../api";

const LEVEL_COLOR: Record<string, string> = {
  good: "#3fb950",
  neutral: "#f0a020",
  caution: "#f0506e",
};

export default function PlanInsights({ planId }: { planId: number }) {
  const [h, setH] = useState<HealthScore | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.planHealth(planId).then(setH).catch(() => setErr(true));
  }, [planId]);

  if (err) return null;
  if (!h) return <div className="card muted">計算健康度…</div>;

  const color = LEVEL_COLOR[h.level] || "#93a1b3";
  const dash = 2 * Math.PI * 42;

  return (
    <div className="card">
      <div className="section-title">計畫健康度</div>
      <div className="row" style={{ gap: 24, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", width: 110, height: 110 }}>
          <svg width="110" height="110" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border)" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="42" fill="none" stroke={color} strokeWidth="8"
              strokeLinecap="round" strokeDasharray={dash}
              strokeDashoffset={dash * (1 - h.score / 100)}
              transform="rotate(-90 50 50)"
            />
            <text x="50" y="46" textAnchor="middle" fontSize="26" fontWeight="700" fill="var(--text)">
              {h.score}
            </text>
            <text x="50" y="64" textAnchor="middle" fontSize="11" fill="var(--muted)">/ 100</text>
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ color, fontWeight: 700, fontSize: 18, marginBottom: 6 }}>{h.label}</div>
          <div className="row" style={{ gap: 16, flexWrap: "wrap", marginBottom: 8 }}>
            <span className="muted">本益比 <b style={{ color: "var(--text)" }}>{h.per ?? "—"}</b></span>
            <span className="muted">股價淨值比 <b style={{ color: "var(--text)" }}>{h.pbr ?? "—"}</b></span>
            <span className="muted">現金殖利率 <b style={{ color: "var(--text)" }}>{h.dividend_yield != null ? `${h.dividend_yield}%` : "—"}</b></span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, color: "var(--muted)", fontSize: 13, lineHeight: 1.7 }}>
            {h.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
