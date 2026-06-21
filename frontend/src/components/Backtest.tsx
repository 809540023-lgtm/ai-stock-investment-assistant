import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, Backtest as BacktestData, Plan } from "../api";

const C = {
  green: "#3fb950",
  muted: "#93a1b3",
  border: "#2c3a4f",
  panel: "#1a2230",
  text: "#e6edf3",
  danger: "#f0506e",
};

function fmt(n?: number) {
  return n == null ? "—" : n.toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}
function fmtTick(d: string) {
  const [y, m] = d.split("-");
  return `${y.slice(2)}/${m}`;
}

export default function Backtest({ plan }: { plan: Plan }) {
  const [monthly, setMonthly] = useState<number>(plan.monthly_amount || 3000);
  const [years, setYears] = useState<number>(plan.investment_years || 3);
  const [data, setData] = useState<BacktestData | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    setBusy(true);
    setErr("");
    try {
      setData(await api.backtest(plan.id, monthly, years));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const profit = (data?.total_return_percent ?? 0) >= 0;

  return (
    <div className="card">
      <div className="section-title">策略回測 ・ 定期定額試算</div>
      <p className="muted" style={{ marginTop: -6 }}>
        假設過去每月固定買進（含零股），回算到今天的績效。
      </p>

      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <label>每月投入（元）</label>
          <input
            type="number"
            value={monthly}
            min={1000}
            step={1000}
            onChange={(e) => setMonthly(Number(e.target.value))}
            style={{ width: 140 }}
          />
        </div>
        <div>
          <label>回測年數</label>
          <input
            type="number"
            value={years}
            min={1}
            max={10}
            step={1}
            onChange={(e) => setYears(Number(e.target.value))}
            style={{ width: 100 }}
          />
        </div>
        <button onClick={run} disabled={busy} style={{ height: 40 }}>
          {busy ? "試算中…" : "開始回測"}
        </button>
      </div>

      {err && <div className="error" style={{ marginTop: 12 }}>{err}</div>}

      {data && !data.available && (
        <div className="muted" style={{ marginTop: 12 }}>{data.reason || "無法回測"}</div>
      )}

      {data && data.available && (
        <>
          <div className="grid-cards" style={{ marginTop: 16 }}>
            <div className="card">
              <div className="tag">期間 / 累積投入</div>
              <div className="metric" style={{ fontSize: 18 }}>
                {data.years} 年・{data.months} 期
              </div>
              <div className="muted" style={{ fontSize: 13 }}>${fmt(data.total_invested)}</div>
            </div>
            <div className="card">
              <div className="tag">目前市值</div>
              <div className="metric">${fmt(data.final_value)}</div>
            </div>
            <div className="card">
              <div className="tag">總報酬率</div>
              <div className="metric" style={{ color: profit ? C.green : C.danger }}>
                {profit ? "+" : ""}
                {data.total_return_percent}%
              </div>
            </div>
            <div className="card">
              <div className="tag">年化報酬率</div>
              <div className="metric" style={{ color: profit ? C.green : C.danger }}>
                {(data.annualized_return_percent ?? 0) >= 0 ? "+" : ""}
                {data.annualized_return_percent}%
              </div>
            </div>
            <div className="card">
              <div className="tag">最大回撤</div>
              <div className="metric" style={{ color: C.danger, fontSize: 22 }}>
                -{data.max_drawdown_percent}%
              </div>
            </div>
          </div>

          {data.benchmark && (
            <div
              className="card"
              style={{ marginTop: 12, background: "rgba(79,140,255,0.06)", borderColor: "var(--accent)" }}
            >
              <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <span>
                  同期改投 <b>大盤 ETF {data.benchmark.symbol}</b>：
                  <b style={{ color: (data.benchmark.total_return_percent ?? 0) >= 0 ? C.green : C.danger }}>
                    {" "}{data.benchmark.total_return_percent >= 0 ? "+" : ""}{data.benchmark.total_return_percent}%
                  </b>
                </span>
                <span>
                  本檔{" "}
                  <b style={{ color: data.benchmark.outperformance_percent >= 0 ? C.green : C.danger }}>
                    {data.benchmark.outperformance_percent >= 0 ? "勝出 +" : "落後 "}
                    {data.benchmark.outperformance_percent}%
                  </b>
                </span>
              </div>
            </div>
          )}

          <div style={{ width: "100%", height: 260, marginTop: 12 }}>
            <ResponsiveContainer>
              <AreaChart data={data.series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gVal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={C.green} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={C.green} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickFormatter={fmtTick} minTickGap={48} tick={{ fill: C.muted, fontSize: 12 }} stroke={C.border} />
                <YAxis tick={{ fill: C.muted, fontSize: 12 }} stroke={C.border} width={56} tickFormatter={(v) => (v >= 10000 ? `${Math.round(v / 1000)}k` : `${v}`)} />
                <Tooltip
                  contentStyle={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }}
                  labelStyle={{ color: C.muted }}
                  formatter={(v: number, n) => [`$${fmt(v)}`, n === "value" ? "市值" : "累積投入"]}
                />
                <Legend formatter={(v) => (v === "value" ? "資產市值" : "累積投入")} wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="invested" stroke={C.muted} fill="none" strokeWidth={1.5} strokeDasharray="4 3" name="invested" />
                <Area type="monotone" dataKey="value" stroke={C.green} fill="url(#gVal)" strokeWidth={2} name="value" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="muted" style={{ fontSize: 12 }}>
            ※ 以 {data.start_date} ～ {data.end_date} 實際收盤價回算，未計手續費與股利；過去績效不代表未來。
          </p>
        </>
      )}
    </div>
  );
}
