import { useEffect, useState } from "react";
import { api, WatchItem } from "../api";
import StockSearch from "../components/StockSearch";

export default function Watchlist() {
  const [items, setItems] = useState<WatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState<{ symbol: string; name: string } | null>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");

  const load = () => {
    api.watchlist().then(setItems).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const add = async () => {
    if (!picked) return;
    setErr("");
    try {
      await api.addWatch(picked.symbol, note || undefined);
      setPicked(null);
      setNote("");
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const remove = async (id: number) => {
    await api.removeWatch(id);
    load();
  };

  return (
    <div>
      <h1 className="page-title">觀察清單</h1>
      <p className="page-sub">追蹤有興趣但還沒建立計畫的股票，掌握即時報價。</p>

      <div className="card">
        <div className="section-title">加入股票</div>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 260, flex: 1 }}>
            <label>股票</label>
            <StockSearch value={picked?.symbol || ""} onPick={(symbol, name) => setPicked({ symbol, name })} />
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <label>備註（選填）</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="例如：等回檔" />
          </div>
          <button onClick={add} disabled={!picked} style={{ height: 40 }}>加入</button>
        </div>
        {picked && <p className="muted" style={{ marginTop: 8 }}>已選：{picked.symbol} {picked.name}</p>}
        {err && <div className="error" style={{ marginTop: 8 }}>{err}</div>}
      </div>

      <div className="card">
        <div className="section-title">追蹤中（{items.length}）</div>
        {loading ? (
          <div className="muted">載入中…</div>
        ) : items.length === 0 ? (
          <p className="muted">尚無觀察股票，從上方加入第一檔。</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 13 }}>
                <th style={{ padding: "8px 4px" }}>股票</th>
                <th>現價</th>
                <th>漲跌</th>
                <th>備註</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} style={{ borderTop: "1px solid var(--border)", fontSize: 14 }}>
                  <td style={{ padding: "10px 4px" }}>
                    <b>{it.stock_name}</b>（{it.stock_symbol}）
                  </td>
                  <td>{it.current_price ?? "—"}</td>
                  <td className={it.change_percent == null ? "muted" : it.change_percent >= 0 ? "action take_profit" : "action stop_loss"}>
                    {it.change_percent == null ? "—" : `${it.change_percent >= 0 ? "+" : ""}${it.change_percent}%`}
                  </td>
                  <td className="muted">{it.note || "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="ghost small" onClick={() => remove(it.id)}>移除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
