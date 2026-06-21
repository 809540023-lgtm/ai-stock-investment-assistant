import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, PlanChart } from "../api";

const C = {
  accent: "#4f8cff",
  warn: "#f0a020",
  muted: "#93a1b3",
  border: "#2c3a4f",
  panel: "#1a2230",
  text: "#e6edf3",
};

function fmtTick(d: string) {
  // YYYY-MM-DD -> YY/MM
  const [y, m] = d.split("-");
  return `${y.slice(2)}/${m}`;
}

export default function PriceChart({ planId }: { planId: number }) {
  const [data, setData] = useState<PlanChart | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.chart(planId).then(setData).catch((e) => setErr(e.message));
  }, [planId]);

  if (err) return null;
  if (!data) return <div className="card muted">載入股價圖…</div>;
  if (!data.prices.length)
    return <div className="card muted">查無股價資料，無法繪圖。</div>;

  const closes = data.prices.map((p) => p.close);
  const lo = Math.min(...closes);
  const hi = Math.max(...closes);
  const pad = (hi - lo) * 0.08 || 1;

  return (
    <div className="card">
      <div className="section-title">股價走勢（近一年）</div>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <LineChart data={data.prices} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={fmtTick}
              minTickGap={48}
              tick={{ fill: C.muted, fontSize: 12 }}
              stroke={C.border}
            />
            <YAxis
              domain={[Math.floor(lo - pad), Math.ceil(hi + pad)]}
              tick={{ fill: C.muted, fontSize: 12 }}
              stroke={C.border}
              width={48}
            />
            <Tooltip
              contentStyle={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }}
              labelStyle={{ color: C.muted }}
              formatter={(v: number) => [`${v}`, "收盤"]}
            />
            <Line type="monotone" dataKey="close" stroke={C.accent} strokeWidth={2} dot={false} name="收盤價" />
            {data.average_cost != null && (
              <ReferenceLine
                y={data.average_cost}
                stroke={C.warn}
                strokeDasharray="5 4"
                label={{ value: `成本 ${data.average_cost}`, position: "insideTopLeft", fill: C.warn, fontSize: 12 }}
              />
            )}
            {data.avg_price_1y != null && (
              <ReferenceLine
                y={data.avg_price_1y}
                stroke={C.muted}
                strokeDasharray="2 4"
                label={{ value: `一年均價 ${data.avg_price_1y}`, position: "insideBottomLeft", fill: C.muted, fontSize: 12 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="row muted" style={{ fontSize: 12, gap: 16, flexWrap: "wrap" }}>
        <span>● <span style={{ color: C.accent }}>收盤價</span></span>
        {data.average_cost != null && <span>┄ <span style={{ color: C.warn }}>你的持股成本</span></span>}
        {data.avg_price_1y != null && <span>┄ <span style={{ color: C.muted }}>一年均價</span></span>}
        <span>區間 {data.low_52w}–{data.high_52w}</span>
      </div>
    </div>
  );
}
