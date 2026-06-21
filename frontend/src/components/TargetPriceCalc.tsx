import { useEffect, useState } from "react";
import { api, Plan } from "../api";

/** 目標價試算：EPS × 目標本益比 = 合理/目標股價，並對比目前股價。 */
export default function TargetPriceCalc({ plan }: { plan: Plan }) {
  const [eps, setEps] = useState<number>(0);
  const [targetPer, setTargetPer] = useState<number>(20);
  const cur = plan.current_price || 0;

  useEffect(() => {
    // 用最新本益比 + 現價回推 EPS 當預設值
    api.valuation(plan.stock_symbol).then((v) => {
      if (v.per && cur) setEps(Number((cur / v.per).toFixed(2)));
      if (v.per) setTargetPer(Math.round(v.per));
    }).catch(() => {});
  }, [plan.stock_symbol]);

  const target = eps > 0 ? Math.round(eps * targetPer) : 0;
  const upside = cur && target ? ((target - cur) / cur) * 100 : 0;

  return (
    <div className="card">
      <div className="section-title">目標價試算器</div>
      <p className="muted" style={{ marginTop: -6 }}>
        以「每股盈餘 EPS × 目標本益比」推算合理股價。
      </p>
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <label>預估 EPS（元）</label>
          <input type="number" step="0.1" value={eps} onChange={(e) => setEps(Number(e.target.value))} style={{ width: 120 }} />
        </div>
        <div>
          <label>目標本益比</label>
          <input type="number" step="1" value={targetPer} onChange={(e) => setTargetPer(Number(e.target.value))} style={{ width: 110 }} />
        </div>
      </div>
      {target > 0 && (
        <div className="grid-cards" style={{ marginTop: 14 }}>
          <div className="card">
            <div className="tag">推算目標價</div>
            <div className="metric">${target}</div>
          </div>
          <div className="card">
            <div className="tag">目前股價</div>
            <div className="metric">${cur || "—"}</div>
          </div>
          <div className="card">
            <div className="tag">潛在空間</div>
            <div className="metric" style={{ color: upside >= 0 ? "#3fb950" : "#f0506e" }}>
              {upside >= 0 ? "+" : ""}{upside.toFixed(1)}%
            </div>
          </div>
        </div>
      )}
      <p className="muted" style={{ fontSize: 12 }}>※ 僅為簡易試算，EPS 與合理本益比請依最新財報與產業判斷。</p>
    </div>
  );
}
