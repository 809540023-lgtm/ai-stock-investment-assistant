import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, PerBand } from "../api";

const C = {
  accent: "#4f8cff",
  warn: "#f0a020",
  green: "#3fb950",
  danger: "#f0506e",
  muted: "#93a1b3",
  border: "#2c3a4f",
  panel: "#1a2230",
  text: "#e6edf3",
};

function fmtTick(d: string) {
  const [y, m] = d.split("-");
  return `${y.slice(2)}/${m}`;
}

export default function StockAnalytics({ symbol }: { symbol: string }) {
  const [band, setBand] = useState<PerBand | null>(null);
  const [inst, setInst] = useState<{ date: string; net_lots: number }[] | null>(null);

  useEffect(() => {
    api.perBand(symbol).then(setBand).catch(() => setBand(null));
    api.institutional(symbol).then((d) => setInst(d.data)).catch(() => setInst(null));
  }, [symbol]);

  return (
    <>
      <div className="card">
        <div className="section-title">本益比河流圖（近一年）</div>
        {band && band.history.length ? (
          <>
            <div style={{ width: "100%", height: 240 }}>
              <ResponsiveContainer>
                <LineChart data={band.history} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={fmtTick} minTickGap={48} tick={{ fill: C.muted, fontSize: 12 }} stroke={C.border} />
                  <YAxis tick={{ fill: C.muted, fontSize: 12 }} stroke={C.border} width={40} />
                  <Tooltip contentStyle={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }} formatter={(v: number) => [`${v}`, "本益比"]} />
                  {band.bands && (
                    <>
                      <ReferenceLine y={band.bands.low} stroke={C.green} strokeDasharray="4 4" label={{ value: `便宜 ${band.bands.low}`, position: "insideBottomLeft", fill: C.green, fontSize: 11 }} />
                      <ReferenceLine y={band.bands.mid} stroke={C.muted} strokeDasharray="2 4" label={{ value: `中位 ${band.bands.mid}`, position: "insideLeft", fill: C.muted, fontSize: 11 }} />
                      <ReferenceLine y={band.bands.high} stroke={C.danger} strokeDasharray="4 4" label={{ value: `昂貴 ${band.bands.high}`, position: "insideTopLeft", fill: C.danger, fontSize: 11 }} />
                    </>
                  )}
                  <Line type="monotone" dataKey="per" stroke={C.accent} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="muted" style={{ fontSize: 12 }}>
              藍線為每日本益比；綠線（10 百分位）以下偏便宜、紅線（90 百分位）以上偏貴。
            </p>
          </>
        ) : (
          <div className="muted">查無本益比資料。</div>
        )}
      </div>

      <div className="card">
        <div className="section-title">三大法人買賣超（近 30 日・張）</div>
        {inst && inst.length ? (
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={inst} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickFormatter={fmtTick} minTickGap={36} tick={{ fill: C.muted, fontSize: 11 }} stroke={C.border} />
                <YAxis tick={{ fill: C.muted, fontSize: 12 }} stroke={C.border} width={52} />
                <Tooltip contentStyle={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }} formatter={(v: number) => [`${v} 張`, v >= 0 ? "買超" : "賣超"]} />
                <ReferenceLine y={0} stroke={C.muted} />
                <Bar dataKey="net_lots">
                  {inst.map((e, i) => (
                    <Cell key={i} fill={e.net_lots >= 0 ? C.green : C.danger} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="muted">查無法人籌碼資料。</div>
        )}
      </div>
    </>
  );
}
