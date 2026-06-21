import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Plan } from "../api";
import TradeRecords from "../components/TradeRecords";
import PriceChart from "../components/PriceChart";
import Backtest from "../components/Backtest";
import PlanInsights from "../components/PlanInsights";
import StockAnalytics from "../components/StockAnalytics";
import TargetPriceCalc from "../components/TargetPriceCalc";

const RISK_LABEL: Record<string, string> = {
  conservative: "保守型",
  balanced: "穩健型",
  aggressive: "積極型",
};

function Section({ title, text }: { title: string; text: string | null }) {
  if (!text) return null;
  return (
    <div className="card">
      <div className="section-title">{title}</div>
      <pre className="analysis">{text}</pre>
    </div>
  );
}

export default function PlanResult() {
  const { id } = useParams();
  const nav = useNavigate();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    api.getPlan(Number(id)).then(setPlan).catch((e) => setError(e.message));
  };
  useEffect(load, [id]);

  const reanalyze = async () => {
    setBusy(true);
    try {
      setPlan(await api.analyzePlan(Number(id)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <div className="error">{error}</div>;
  if (!plan) return <div>載入中…</div>;

  const isRecurring = plan.plan_type === "recurring_investment";

  return (
    <div>
      <div className="spread">
        <div>
          <h1 className="page-title">
            {plan.stock_name}（{plan.stock_symbol}）
          </h1>
          <p className="page-sub">
            <span className={"pill " + (isRecurring ? "recurring" : "full")}>
              {isRecurring ? "零存整付投資計劃" : "完整股票分析計劃"}
            </span>{" "}
            <span className={"pill status-" + plan.status}>{plan.status}</span>
          </p>
        </div>
        <div className="row">
          <button className="ghost small" onClick={reanalyze} disabled={busy}>
            {busy ? "更新中…" : "重新分析"}
          </button>
          <Link to={`/plans/${plan.id}/updates`}>
            <button className="ghost small">每月更新紀錄</button>
          </Link>
        </div>
      </div>

      <div className="grid-cards">
        <div className="card">
          <div className="tag">目前股價</div>
          <div className="metric">{plan.current_price ?? "—"}</div>
        </div>
        {isRecurring ? (
          <>
            <div className="card">
              <div className="tag">每月投入</div>
              <div className="metric">${plan.monthly_amount}</div>
            </div>
            <div className="card">
              <div className="tag">建議每月買進比例</div>
              <div className="metric">
                {plan.fixed_buy_ratio != null ? `${Math.round(plan.fixed_buy_ratio * 100)}%` : "—"}
              </div>
            </div>
            <div className="card">
              <div className="tag">建議現金保留比例</div>
              <div className="metric">
                {plan.cash_reserve_ratio != null ? `${Math.round(plan.cash_reserve_ratio * 100)}%` : "—"}
              </div>
            </div>
            <div className="card">
              <div className="tag">風險偏好 / 年限</div>
              <div className="metric" style={{ fontSize: 18 }}>
                {RISK_LABEL[plan.risk_profile || ""] || "—"} / {plan.investment_years ?? "—"} 年
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="card">
              <div className="tag">持股成本</div>
              <div className="metric">{plan.average_cost ?? "—"}</div>
            </div>
            <div className="card">
              <div className="tag">目標報酬 / 最大虧損</div>
              <div className="metric" style={{ fontSize: 18 }}>
                +{plan.target_return_percent ?? "—"}% / -{plan.max_loss_percent ?? "—"}%
              </div>
            </div>
          </>
        )}
      </div>

      <PlanInsights planId={plan.id} />

      <PriceChart planId={plan.id} />

      <StockAnalytics symbol={plan.stock_symbol} />

      {plan.ai_summary && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <div className="section-title">AI 投資摘要</div>
          <pre className="analysis">{plan.ai_summary}</pre>
        </div>
      )}

      <TargetPriceCalc plan={plan} />

      {isRecurring && <Backtest plan={plan} />}

      <TradeRecords plan={plan} onPlanChange={setPlan} />

      <Section title="基本面分析" text={plan.fundamental_analysis} />
      <Section title="估值分析" text={plan.valuation_analysis} />
      <Section title="買進規則" text={plan.buy_strategy} />
      <Section title="加碼規則" text={plan.add_position_strategy} />
      <Section title="暫停投入規則" text={plan.pause_strategy} />
      <Section title="停利／停損規則" text={plan.sell_strategy} />
      <Section title="風險提醒" text={plan.risk_notes} />

      <button
        className="ghost small"
        onClick={() => nav("/plans")}
        style={{ marginTop: 8 }}
      >
        ← 回到我的投資計畫
      </button>
    </div>
  );
}
