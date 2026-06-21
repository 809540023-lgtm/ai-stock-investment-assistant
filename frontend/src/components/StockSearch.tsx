import { useEffect, useRef, useState } from "react";
import { api, StockHit } from "../api";

/** 台股搜尋自動完成。value 為股票代號；選取時回傳代號與名稱。 */
export default function StockSearch({
  value,
  onPick,
}: {
  value: string;
  onPick: (symbol: string, name: string) => void;
}) {
  const [q, setQ] = useState(value);
  const [hits, setHits] = useState<StockHit[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => setQ(value), [value]);

  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      api.searchStocks(q.trim()).then(setHits).catch(() => setHits([]));
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={box} style={{ position: "relative" }}>
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="輸入代號或名稱，例如 2330 或 台積電"
        autoComplete="off"
      />
      {open && hits.length > 0 && (
        <div
          style={{
            position: "absolute", zIndex: 20, top: "100%", left: 0, right: 0,
            background: "var(--panel)", border: "1px solid var(--border)",
            borderRadius: 8, marginTop: 4, maxHeight: 260, overflowY: "auto",
            boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
          }}
        >
          {hits.map((h) => (
            <div
              key={h.symbol}
              onClick={() => {
                onPick(h.symbol, h.name);
                setQ(h.symbol);
                setOpen(false);
              }}
              style={{ padding: "8px 12px", cursor: "pointer", display: "flex", gap: 10 }}
              onMouseDown={(e) => e.preventDefault()}
              className="search-hit"
            >
              <b style={{ color: "var(--accent)", minWidth: 48 }}>{h.symbol}</b>
              <span>{h.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
