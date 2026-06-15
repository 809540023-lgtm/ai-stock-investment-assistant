import { FormEvent, useEffect, useState } from "react";
import { api, Plan, Trade } from "../api";

export default function TradeRecords({
  plan,
  onPlanChange,
}: {
  plan: Plan;
  onPlanChange: (p: Plan) => void;
}) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [action, setAction] = useState<"buy" | "sell">("buy");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState(plan.current_price ? String(plan.current_price) : "");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.trades(plan.id).then(setTrades).catch(() => setTrades([]));
  useEffect(() => {
    load();
  }, [plan.id]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const updated = await api.addTrade(plan.id, {
        action,
        shares: Number(shares),
        price: Number(price),
        note: note || null,
      });
      onPlanChange(updated);
      setShares("");
      setNote("");
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("刪除這筆交易紀錄？均價會重新計算。")) return;
    const updated = await api.deleteTrade(plan.id, id);
    onPlanChange(updated);
    load();
  };

  return (
    <div className="card">
      <div className="section-title">實際買進／賣出紀錄</div>
      <form onSubmit={submit} className="row" style={{ flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
        <div style={{ width: 110 }}>
          <label>動作</label>
          <select value={action} onChange={(e) => setAction(e.target.value as "buy" | "sell")}>
            <option value="buy">買進</option>
            <option value="sell">賣出</option>
          </select>
        </div>
        <div style={{ width: 110 }}>
          <label>股數</label>
          <input type="number" step="1" value={shares} onChange={(e) => setShares(e.target.value)} required />
        </div>
        <div style={{ width: 130 }}>
          <label>成交價</label>
          <input type="number" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} required />
        </div>
        <div style={{ flex: 1, minWidth: 140 }}>
          <label>備註（選填）</label>
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="例如：回檔加碼" />
        </div>
        <button type="submit" disabled={busy}>
          {busy ? "新增中…" : "新增紀錄"}
        </button>
      </form>
      {error && <div className="error">{error}</div>}

      <div className="divider" />
      <div className="row" style={{ gap: 24 }}>
        <div>
          <div className="tag">目前持股</div>
          <div className="metric" style={{ fontSize: 18 }}>{plan.shares_owned ?? 0} 股</div>
        </div>
        <div>
          <div className="tag">平均成本</div>
          <div className="metric" style={{ fontSize: 18 }}>{plan.average_cost ?? "—"}</div>
        </div>
      </div>

      {trades.length === 0 ? (
        <p className="muted" style={{ marginTop: 12 }}>尚無交易紀錄。新增後會自動重算持股與平均成本。</p>
      ) : (
        <table style={{ width: "100%", marginTop: 14, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 13 }}>
              <th style={{ padding: "6px 4px" }}>日期</th>
              <th>動作</th>
              <th>股數</th>
              <th>成交價</th>
              <th>備註</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id} style={{ borderTop: "1px solid var(--border)", fontSize: 14 }}>
                <td style={{ padding: "8px 4px" }}>{new Date(t.traded_at).toLocaleDateString("zh-TW")}</td>
                <td>
                  <span className={"action " + (t.action === "buy" ? "buy" : "stop_loss")}>
                    {t.action === "buy" ? "買進" : "賣出"}
                  </span>
                </td>
                <td>{t.shares}</td>
                <td>{t.price}</td>
                <td className="muted">{t.note || "—"}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="ghost small" onClick={() => remove(t.id)}>刪</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
