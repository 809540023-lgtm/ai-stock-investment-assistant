import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import StockSearch from "../components/StockSearch";

export default function RecurringForm() {
  const nav = useNavigate();
  const [symbol, setSymbol] = useState("");
  const [monthly, setMonthly] = useState("3000");
  const [years, setYears] = useState("5");
  const [risk, setRisk] = useState("balanced");
  const [target, setTarget] = useState("30");
  const [maxLoss, setMaxLoss] = useState("20");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const plan = await api.createPlan({
        plan_type: "recurring_investment",
        stock_symbol: symbol,
        monthly_amount: Number(monthly),
        investment_years: years ? Number(years) : null,
        risk_profile: risk,
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
      <h1 className="page-title">零存整付投資計劃</h1>
      <p className="page-sub">設定每月投入金額，AI 會試算每月買進比例、現金保留與加碼／暫停規則</p>
      <form onSubmit={submit} className="card" style={{ maxWidth: 640 }}>
        <label>股票（輸入代號或名稱搜尋）</label>
        <StockSearch value={symbol} onPick={(s) => setSymbol(s)} />
        <div className="grid-2">
          <div>
            <label>每月投入金額（元）</label>
            <input type="number" value={monthly} onChange={(e) => setMonthly(e.target.value)} required />
          </div>
          <div>
            <label>投資年限（年）</label>
            <input type="number" value={years} onChange={(e) => setYears(e.target.value)} />
          </div>
        </div>
        <label>風險偏好</label>
        <select value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="conservative">保守型</option>
          <option value="balanced">穩健型</option>
          <option value="aggressive">積極型</option>
        </select>
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
          {busy ? "AI 試算中…" : "產生每月投入計畫"}
        </button>
      </form>
    </div>
  );
}
