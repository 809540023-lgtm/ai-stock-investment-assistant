import { useEffect, useState } from "react";
import { api, Plan } from "../api";

/** 存股目標試算：想每年領 X 元股利，需要幾張、投入多少本金。 */
export default function DividendGoal({ plan }: { plan: Plan }) {
  const [targetIncome, setTargetIncome] = useState<number>(120000);
  const [dps, setDps] = useState<number>(0); // 每股現金股利
  const price = plan.current_price || 0;

  useEffect(() => {
    Promise.all([api.dividends(plan.stock_symbol), api.valuation(plan.stock_symbol)])
      .then(([d, v]) => {
        const last = d.data[d.data.length - 1];
        if (last && last.cash) setDps(Number(last.cash.toFixed(2)));
        else if (v.dividend_yield && price) setDps(Number(((v.dividend_yield / 100) * price).toFixed(2)));
      })
      .catch(() => {});
  }, [plan.stock_symbol]);

  const sharesNeeded = dps > 0 ? Math.ceil(targetIncome / dps) : 0;
  const lots = sharesNeeded ? (sharesNeeded / 1000).toFixed(1) : "—";
  const capital = sharesNeeded && price ? Math.round(sharesNeeded * price) : 0;
  const yieldPct = dps && price ? ((dps / price) * 100).toFixed(2) : "—";

  return (
    <div className="card">
      <div className="section-title">存股目標試算</div>
      <p className="muted" style={{ marginTop: -6 }}>
        想靠這檔每年領到固定股利，需要存多少？（每股現金股利 {dps || "—"} 元・殖利率 {yieldPct}%）
      </p>
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <label>目標年股利（元）</label>
          <input type="number" step="10000" value={targetIncome} onChange={(e) => setTargetIncome(Number(e.target.value))} style={{ width: 150 }} />
        </div>
        <div>
          <label>每股現金股利（元）</label>
          <input type="number" step="0.1" value={dps} onChange={(e) => setDps(Number(e.target.value))} style={{ width: 140 }} />
        </div>
      </div>
      {sharesNeeded > 0 && (
        <div className="grid-cards" style={{ marginTop: 14 }}>
          <div className="card">
            <div className="tag">需要股數</div>
            <div className="metric" style={{ fontSize: 20 }}>{sharesNeeded.toLocaleString()} 股</div>
            <div className="muted" style={{ fontSize: 13 }}>約 {lots} 張</div>
          </div>
          <div className="card">
            <div className="tag">預估投入本金</div>
            <div className="metric">${capital.toLocaleString()}</div>
          </div>
          <div className="card">
            <div className="tag">目前殖利率</div>
            <div className="metric" style={{ color: "#3fb950" }}>{yieldPct}%</div>
          </div>
        </div>
      )}
      <p className="muted" style={{ fontSize: 12 }}>※ 以最近一次現金股利估算，未來配息會變動，僅供參考。</p>
    </div>
  );
}
