import { useNavigate } from "react-router-dom";

export default function CreatePlan() {
  const nav = useNavigate();
  return (
    <div>
      <h1 className="page-title">建立投資計畫</h1>
      <p className="page-sub">選擇你想要的計畫類型</p>
      <div className="grid-2">
        <div className="card choice-card" onClick={() => nav("/create/full")}>
          <span className="pill full">模式 A</span>
          <h2 style={{ margin: "12px 0 8px" }}>完整股票分析計劃</h2>
          <p className="muted">
            適合想深入研究一檔股票的人。重點是基本面、估值、產業循環、風險、
            停利停損與長期持有判斷。
          </p>
          <button className="ghost small">選擇這個 →</button>
        </div>
        <div className="card choice-card" onClick={() => nav("/create/recurring")}>
          <span className="pill recurring">模式 B</span>
          <h2 style={{ margin: "12px 0 8px" }}>零存整付投資計劃</h2>
          <p className="muted">
            適合每月固定存 3,000、5,000、10,000 的會員。重點是每月投入多少、
            買多少股、保留多少現金、什麼價格加碼或暫停。
          </p>
          <button className="ghost small">選擇這個 →</button>
        </div>
      </div>
    </div>
  );
}
