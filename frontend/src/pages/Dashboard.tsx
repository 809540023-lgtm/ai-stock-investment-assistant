import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Dashboard as DashboardData } from "../api";

function pnlClass(v: number) {
  return v > 0 ? "action take_profit" : v < 0 ? "action stop_loss" : "muted";
}
function fmt(n: number) {
  return n.toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>載入中…</div>;
  if (!data) return <div className="error">無法載入總覽</div>;

  return (
    <div>
      <h1 className="page-title">投資總覽</h1>
      <p className="page-sub">所有計畫的投入成本、市值與未實現損益</p>

      <div className="grid-cards">
        <div className="card">
          <div className="tag">計畫數</div>
          <div className="metric">{data.plan_count}</div>
        </div>
        <div className="card">
          <div className="tag">投入成本</div>
          <div className="metric">${fmt(data.total_invested)}</div>
        </div>
        <div className="card">
          <div className="tag">目前市值</div>
          <div className="metric">${fmt(data.total_market_value)}</div>
        </div>
        <div className="card">
          <div className="tag">未實現損益</div>
          <div className={"metric " + pnlClass(data.total_unrealized_pnl)}>
            {data.total_unrealized_pnl >= 0 ? "+" : ""}
            ${fmt(data.total_unrealized_pnl)}
            {data.total_unrealized_pnl_percent != null && (
              <span style={{ fontSize: 14 }}> （{data.total_unrealized_pnl_percent}%）</span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="section-title">各計畫明細</div>
        {data.plans.length === 0 ? (
          <p className="muted">尚無計畫，<Link to="/create">建立第一個</Link>。</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 13 }}>
                <th style={{ padding: "8px 4px" }}>股票</th>
                <th>類型</th>
                <th>持股</th>
                <th>均價</th>
                <th>現價</th>
                <th>投入</th>
                <th>市值</th>
                <th>未實現損益</th>
              </tr>
            </thead>
            <tbody>
              {data.plans.map((p) => (
                <tr key={p.id} style={{ borderTop: "1px solid var(--border)", fontSize: 14 }}>
                  <td style={{ padding: "10px 4px" }}>
                    <Link to={`/plans/${p.id}`}>
                      {p.stock_name}（{p.stock_symbol}）
                    </Link>
                  </td>
                  <td>
                    <span className={"pill " + (p.plan_type === "recurring_investment" ? "recurring" : "full")}>
                      {p.plan_type === "recurring_investment" ? "零存整付" : "完整分析"}
                    </span>
                  </td>
                  <td>{p.shares_owned || "—"}</td>
                  <td>{p.average_cost ?? "—"}</td>
                  <td>{p.current_price ?? "—"}</td>
                  <td>${fmt(p.invested)}</td>
                  <td>${fmt(p.market_value)}</td>
                  <td className={pnlClass(p.unrealized_pnl)}>
                    {p.invested ? (
                      <>
                        {p.unrealized_pnl >= 0 ? "+" : ""}${fmt(p.unrealized_pnl)}
                        {p.unrealized_pnl_percent != null && ` (${p.unrealized_pnl_percent}%)`}
                      </>
                    ) : (
                      "—"
                    )}
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
