import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, UpdateLog } from "../api";

const ACTION_LABEL: Record<string, string> = {
  buy: "買進",
  add: "加碼",
  pause: "暫停投入",
  take_profit: "停利",
  stop_loss: "停損",
  hold: "持有",
};

export default function UpdateRecords() {
  const { id } = useParams();
  const [logs, setLogs] = useState<UpdateLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .planUpdates(Number(id))
      .then(setLogs)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div>載入中…</div>;

  return (
    <div>
      <h1 className="page-title">每月更新紀錄</h1>
      <p className="page-sub">每次 AI 重新分析的結果與建議動作</p>
      <Link to={`/plans/${id}`}>← 回到計畫</Link>

      {logs.length === 0 ? (
        <div className="card muted" style={{ marginTop: 16 }}>
          尚無更新紀錄。系統每月 1 號會自動更新，你也可以在計畫頁按「重新分析」。
        </div>
      ) : (
        <div style={{ marginTop: 16 }}>
          {logs.map((l) => (
            <div className="card" key={l.id}>
              <div className="spread">
                <span className={"action " + (l.action || "hold")}>
                  {ACTION_LABEL[l.action || "hold"] || l.action}
                </span>
                <span className="muted" style={{ fontSize: 13 }}>
                  {new Date(l.created_at).toLocaleString("zh-TW")} ・{" "}
                  {l.trigger === "monthly" ? "每月自動" : "手動"} ・ 股價 {l.price_at_update ?? "—"}
                </span>
              </div>
              {l.detail && <p style={{ margin: "10px 0 0" }}>{l.detail}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
