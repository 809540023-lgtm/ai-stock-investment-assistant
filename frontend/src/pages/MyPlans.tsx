import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Plan } from "../api";

export default function MyPlans() {
  const nav = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api
      .listPlans()
      .then(setPlans)
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const remove = async (e: React.MouseEvent, id: number) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("確定刪除這個投資計畫？")) return;
    await api.deletePlan(id);
    load();
  };

  if (loading) return <div>載入中…</div>;

  return (
    <div>
      <div className="spread">
        <div>
          <h1 className="page-title">我的投資計畫</h1>
          <p className="page-sub">共 {plans.length} 個計畫</p>
        </div>
        <button onClick={() => nav("/create")}>＋ 建立新計畫</button>
      </div>

      {plans.length === 0 ? (
        <div className="card center muted">
          還沒有任何計畫，<Link to="/create">建立第一個投資計畫</Link>
        </div>
      ) : (
        <div className="grid-cards">
          {plans.map((p) => {
            const isRecurring = p.plan_type === "recurring_investment";
            return (
              <Link key={p.id} to={`/plans/${p.id}`}>
                <div className="card choice-card">
                  <div className="spread">
                    <span className={"pill " + (isRecurring ? "recurring" : "full")}>
                      {isRecurring ? "零存整付" : "完整分析"}
                    </span>
                    <span className={"pill status-" + p.status}>{p.status}</span>
                  </div>
                  <h2 style={{ margin: "12px 0 4px" }}>
                    {p.stock_name}（{p.stock_symbol}）
                  </h2>
                  <div className="muted" style={{ fontSize: 13 }}>
                    目前股價 {p.current_price ?? "—"}
                    {isRecurring && <> ・ 每月 ${p.monthly_amount}</>}
                  </div>
                  {p.ai_summary && (
                    <p className="muted" style={{ fontSize: 13, marginTop: 10 }}>
                      {p.ai_summary.slice(0, 70)}…
                    </p>
                  )}
                  <button className="danger small" style={{ marginTop: 10 }} onClick={(e) => remove(e, p.id)}>
                    刪除
                  </button>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
