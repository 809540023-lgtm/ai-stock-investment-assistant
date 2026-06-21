import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import StockSearch from "../components/StockSearch";

export default function FullAnalysisForm() {
  const nav = useNavigate();
  const [symbol, setSymbol] = useState("");
  const [averageCost, setAverageCost] = useState("");
  const [shares, setShares] = useState("");
  const [target, setTarget] = useState("25");
  const [maxLoss, setMaxLoss] = useState("15");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const plan = await api.createPlan({
        plan_type: "full_analysis",
        stock_symbol: symbol,
        average_cost: averageCost ? Number(averageCost) : null,
        shares_owned: shares ? Number(shares) : null,
        target_return_percent: target ? Number(target) : null,
        max_loss_percent: maxLoss ? Number(maxLoss) : null,
      });
      const analyzed = await api.analyzePlan(plan.id);
      nav(`/plans/${analyzed.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">完整股票分析計劃</h1>
      <p className="page-sub">輸入股票代號與你的持股狀況，AI 會產生完整分析與操作規則</p>
      <form onSubmit={submit} className="card" style={{ maxWidth: 640 }}>
        <label>股票（輸入代號或名稱搜尋）</label>
        <StockSearch value={symbol} onPick={(s) => setSymbol(s)} />
        <div className="grid-2">
          <div>
            <label>持股成本（選填）</label>
            <input type="number" step="0.01" value={averageCost} onChange={(e) => setAverageCost(e.target.value)} placeholder="例如 580" />
          </div>
          <div>
            <label>持股數（選填）</label>
            <input type="number" step="1" value={shares} onChange={(e) => setShares(e.target.value)} placeholder="例如 1000" />
          </div>
        </div>
        <div className="grid-2">
          <div>
            <label>目標報酬率 (%)</label>
            <input type="number" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div>
            <label>可承受最大虧損 (%)</label>
            <input type="number" value={maxLoss} onChange={(e) => setMaxLoss(e.target.value)} />
          </div>
        </div>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy} style={{ marginTop: 18 }}>
          {busy ? "AI 分析中…" : "產生分析報告"}
        </button>
      </form>
    </div>
  );
}
