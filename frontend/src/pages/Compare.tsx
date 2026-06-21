import { useState } from "react";
import { api, CompareRow } from "../api";
import StockSearch from "../components/StockSearch";

export default function Compare() {
  const [symbols, setSymbols] = useState<string[]>(["2330", "2454"]);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);

  const add = (s: string) => {
    const sym = s.trim().toUpperCase();
    if (sym && !symbols.includes(sym) && symbols.length < 4) setSymbols([...symbols, sym]);
  };
  const removeSym = (s: string) => setSymbols(symbols.filter((x) => x !== s));

  const run = async () => {
    if (!symbols.length) return;
    setLoading(true);
    try {
      setRows(await api.compareStocks(symbols));
    } finally {
      setLoading(false);
    }
  };

  const best = (key: keyof CompareRow, max = true) => {
    const vals = rows.map((r) => r[key]).filter((v) => v != null) as number[];
    if (!vals.length) return null;
    return max ? Math.max(...vals) : Math.min(...vals);
  };
  const bestChange = best("year_change_percent");
  const bestYield = best("dividend_yield");
  const lowPer = best("per", false);

  const cell = (v: number | null, isBest: boolean, suffix = "") =>
    v == null ? "—" : (
      <span style={{ color: isBest ? "#3fb950" : "var(--text)", fontWeight: isBest ? 700 : 400 }}>
        {v}{suffix}
      </span>
    );

  return (
    <div>
      <h1 className="page-title">個股比較</h1>
      <p className="page-sub">最多挑 4 檔股票並列比較漲幅與估值，綠色為該項最佳。</p>

      <div className="card">
        <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: 260, flex: 1 }}>
            <label>加入股票（最多 4 檔）</label>
            <StockSearch value="" onPick={(s) => add(s)} />
          </div>
          <button onClick={run} disabled={loading || !symbols.length} style={{ height: 40 }}>
            {loading ? "比較中…" : "開始比較"}
          </button>
        </div>
        <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          {symbols.map((s) => (
            <span key={s} className="pill full" style={{ cursor: "pointer" }} onClick={() => removeSym(s)}>
              {s} ✕
            </span>
          ))}
        </div>
      </div>

      {rows.length > 0 && (
        <div className="card">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 13 }}>
                <th style={{ padding: "8px 4px" }}>股票</th>
                <th>現價</th>
                <th>近一年漲幅</th>
                <th>本益比</th>
                <th>股價淨值比</th>
                <th>殖利率</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} style={{ borderTop: "1px solid var(--border)", fontSize: 14 }}>
                  <td style={{ padding: "10px 4px" }}><b>{r.name}</b>（{r.symbol}）</td>
                  <td>{r.current_price ?? "—"}</td>
                  <td>{cell(r.year_change_percent, r.year_change_percent === bestChange, "%")}</td>
                  <td>{cell(r.per, r.per === lowPer)}</td>
                  <td>{r.pbr ?? "—"}</td>
                  <td>{cell(r.dividend_yield, r.dividend_yield === bestYield, "%")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
