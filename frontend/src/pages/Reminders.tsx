import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Reminder } from "../api";

const KIND_LABEL: Record<string, string> = {
  buy: "買進",
  add: "加碼",
  pause: "暫停",
  take_profit: "停利",
  stop_loss: "停損",
};

export default function Reminders() {
  const [items, setItems] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api
      .reminders()
      .then(setItems)
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const markRead = async (id: number) => {
    await api.markReminderRead(id);
    load();
  };

  if (loading) return <div>載入中…</div>;

  return (
    <div>
      <h1 className="page-title">提醒中心</h1>
      <p className="page-sub">買進、加碼、暫停、停利／停損提醒</p>

      {items.length === 0 ? (
        <div className="card muted">目前沒有提醒。</div>
      ) : (
        items.map((r) => (
          <div
            className="card spread"
            key={r.id}
            style={{ opacity: r.is_read ? 0.55 : 1 }}
          >
            <div>
              <div className="row">
                <span className={"action " + r.kind}>{KIND_LABEL[r.kind] || r.kind}</span>
                <strong>{r.title}</strong>
                {!r.is_read && <span className="badge">新</span>}
              </div>
              <p style={{ margin: "8px 0 0" }}>{r.message}</p>
              <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                {new Date(r.created_at).toLocaleString("zh-TW")} ・{" "}
                <Link to={`/plans/${r.plan_id}`}>查看計畫</Link>
              </div>
            </div>
            {!r.is_read && (
              <button className="ghost small" onClick={() => markRead(r.id)}>
                標為已讀
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}
