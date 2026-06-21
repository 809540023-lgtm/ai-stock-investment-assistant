import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, FinancialPoint } from "../api";

const C = {
  accent: "#4f8cff",
  warn: "#f0a020",
  green: "#3fb950",
  danger: "#f0506e",
  purple: "#a371f7",
  muted: "#93a1b3",
  border: "#2c3a4f",
  panel: "#1a2230",
  text: "#e6edf3",
};

const tip = {
  contentStyle: { background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text },
  labelStyle: { color: C.muted },
};

const FIN_LABELS: Record<string, string> = {
  gross_margin: "毛利率",
  op_margin: "營益率",
  net_margin: "淨利率",
  eps: "EPS(右)",
};

function q(d: string) {
  const [y, m] = d.split("-");
  const qq = { "03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4" }[m] || m;
  return `${y.slice(2)}${qq}`;
}

export default function StockFundamentals({ symbol }: { symbol: string }) {
  const [rev, setRev] = useState<{ label: string; revenue: number; yoy: number | null }[]>([]);
  const [fin, setFin] = useState<FinancialPoint[]>([]);
  const [div, setDiv] = useState<{ year: string; cash: number; stock: number }[]>([]);
  const [margin, setMargin] = useState<{ date: string; margin_balance: number }[]>([]);

  useEffect(() => {
    api.revenue(symbol).then((d) => setRev(d.data)).catch(() => {});
    api.financials(symbol).then((d) => setFin(d.data)).catch(() => {});
    api.dividends(symbol).then((d) => setDiv(d.data)).catch(() => {});
    api.margin(symbol).then((d) => setMargin(d.data)).catch(() => {});
  }, [symbol]);

  return (
    <>
      <div className="card">
        <div className="section-title">月營收與年增率（近 24 月）</div>
        {rev.length ? (
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <ComposedChart data={rev} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" minTickGap={24} tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} />
                <YAxis yAxisId="l" tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} width={44} />
                <YAxis yAxisId="r" orientation="right" tick={{ fill: C.warn, fontSize: 11 }} stroke={C.border} width={40} unit="%" />
                <Tooltip {...tip} formatter={(v: number, n) => (n === "revenue" ? [`${v} 億`, "營收"] : [`${v}%`, "年增率"])} />
                <Legend formatter={(v) => (v === "revenue" ? "月營收(億)" : "年增率")} wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="l" dataKey="revenue" fill={C.accent} radius={[3, 3, 0, 0]} name="revenue" />
                <Line yAxisId="r" type="monotone" dataKey="yoy" stroke={C.warn} strokeWidth={2} dot={false} name="yoy" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="muted">查無營收資料。</div>
        )}
      </div>

      <div className="card">
        <div className="section-title">獲利能力（EPS 與三率）</div>
        {fin.length ? (
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <ComposedChart data={fin} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickFormatter={q} tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} />
                <YAxis yAxisId="r" tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} width={40} unit="%" />
                <YAxis yAxisId="l" orientation="right" tick={{ fill: C.purple, fontSize: 11 }} stroke={C.border} width={40} />
                <Tooltip {...tip} />
                <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v) => FIN_LABELS[String(v)] || String(v)} />
                <Line yAxisId="r" type="monotone" dataKey="gross_margin" stroke={C.green} strokeWidth={2} dot={false} name="gross_margin" />
                <Line yAxisId="r" type="monotone" dataKey="op_margin" stroke={C.accent} strokeWidth={2} dot={false} name="op_margin" />
                <Line yAxisId="r" type="monotone" dataKey="net_margin" stroke={C.warn} strokeWidth={2} dot={false} name="net_margin" />
                <Line yAxisId="l" type="monotone" dataKey="eps" stroke={C.purple} strokeWidth={2} strokeDasharray="4 3" dot={false} name="eps" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="muted">查無財報資料。</div>
        )}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="section-title">歷年配息</div>
          {div.length ? (
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer>
                <BarChart data={div} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="year" tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} />
                  <YAxis tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} width={32} />
                  <Tooltip {...tip} formatter={(v: number, n) => [`${v} 元`, n === "cash" ? "現金股利" : "股票股利"]} />
                  <Bar dataKey="cash" stackId="d" fill={C.green} name="cash" />
                  <Bar dataKey="stock" stackId="d" fill={C.warn} name="stock" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="muted">查無配息資料。</div>
          )}
        </div>

        <div className="card">
          <div className="section-title">融資餘額（張）</div>
          {margin.length ? (
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer>
                <BarChart data={margin} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} minTickGap={28} tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} />
                  <YAxis tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} width={44} />
                  <Tooltip {...tip} formatter={(v: number) => [`${v} 張`, "融資餘額"]} />
                  <Bar dataKey="margin_balance" fill={C.purple} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="muted">查無融資資料。</div>
          )}
        </div>
      </div>
    </>
  );
}
