import { useEffect, useState } from "react";
import { api, ImportResult, LeadRow, LeadStats } from "../api";

const STATUS_LABEL: Record<string, string> = {
  imported: "待邀請",
  invited: "已邀請",
  consented: "已同意",
  declined: "已婉拒",
  do_not_contact: "拒絕聯繫",
};

const STATUS_FILTERS = ["", "imported", "consented", "do_not_contact"];

export default function Leads() {
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [rows, setRows] = useState<LeadRow[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  // 上傳
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("");
  const [region, setRegion] = useState("TW");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [err, setErr] = useState("");

  // 通話內容（逐字念出的開場白）
  const [script, setScript] = useState("");
  const [scriptDraft, setScriptDraft] = useState("");
  const [scriptSaved, setScriptSaved] = useState(false);

  // 外撥
  const [callMsg, setCallMsg] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([api.leadsStats(), api.listLeads(filter)])
      .then(([s, r]) => {
        setStats(s);
        setRows(r);
      })
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoading(false));
  };
  useEffect(load, [filter]);

  useEffect(() => {
    api
      .getVoiceScript()
      .then((r) => {
        setScript(r.script);
        setScriptDraft(r.script);
      })
      .catch(() => {});
  }, []);

  const saveScript = async () => {
    try {
      const r = await api.setVoiceScript(scriptDraft);
      setScript(r.script);
      setScriptDraft(r.script);
      setScriptSaved(true);
      setTimeout(() => setScriptSaved(false), 2500);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const doImport = async () => {
    if (!file) return;
    setImporting(true);
    setErr("");
    setResult(null);
    try {
      const res = await api.importLeads(file, source, region);
      setResult(res);
      setFile(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setImporting(false);
    }
  };

  const doCall = async (id: number, name: string) => {
    setCallMsg("");
    if (!script.trim()) {
      setCallMsg("尚未設定通話內容，請先在上方「通話內容」填寫並儲存。");
      return;
    }
    if (!window.confirm(`即將致電「${name}」，會逐字念出：\n\n${script}\n\n確定撥出？`)) return;
    try {
      const log = await api.callLead(id);
      setCallMsg(`已發起外撥給「${name}」（狀態：${log.status}）。`);
      load();
    } catch (e) {
      setCallMsg("外撥失敗：" + (e as Error).message);
    }
  };

  return (
    <div>
      <h1 className="page-title">名單與語音外撥</h1>
      <p className="page-sub">
        匯入名單一律為「未同意」。請匯出專屬同意連結、用合法管道邀請；
        對方點同意後（狀態變「已同意」）才可 AI 致電。
      </p>

      {/* 上傳 */}
      <div className="card">
        <div className="section-title">匯入名單（CSV）</div>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <label>CSV 檔</label>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div style={{ minWidth: 140 }}>
            <label>來源標籤</label>
            <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="例：泰山名單" />
          </div>
          <div style={{ minWidth: 120 }}>
            <label>電話國別預設</label>
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="TW">台灣 TW</option>
              <option value="JP">日本 JP</option>
              <option value="US">美國 US</option>
              <option value="HK">香港 HK</option>
              <option value="CN">中國 CN</option>
            </select>
          </div>
          <button onClick={doImport} disabled={!file || importing} style={{ height: 40 }}>
            {importing ? "匯入中…" : "上傳匯入"}
          </button>
        </div>
        {result && (
          <div className="muted" style={{ marginTop: 10 }}>
            匯入完成：新增 <b>{result.added}</b>、重複略過 {result.skipped_duplicates}、
            待人工確認（號碼存疑）{result.needs_review}
          </div>
        )}
        {err && <div className="error" style={{ marginTop: 8 }}>{err}</div>}
      </div>

      {/* 通話內容 */}
      <div className="card">
        <div className="section-title">通話內容（致電時會逐字念出）</div>
        <textarea
          value={scriptDraft}
          onChange={(e) => setScriptDraft(e.target.value)}
          placeholder="例：您好，這裡是林博台股 AI 投資助理，提供您本週的盤後重點與選股提醒。若不需要可隨時說「取消訂閱」。"
          rows={4}
          style={{ width: "100%", resize: "vertical" }}
        />
        <div className="row" style={{ gap: 10, alignItems: "center", marginTop: 8 }}>
          <button onClick={saveScript} disabled={scriptDraft === script}>
            儲存通話內容
          </button>
          {scriptSaved && <span className="action take_profit">已儲存 ✓</span>}
          {!script.trim() && <span className="muted">尚未設定內容，致電會被擋下</span>}
        </div>
        <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
          內容會原封不動念給對方聽（AI 不改寫）。建議包含身分、目的與退訂方式。
        </p>
      </div>

      {/* 統計 */}
      {stats && (
        <div className="card">
          <div className="section-title">名單概況</div>
          <div className="row" style={{ gap: 24, flexWrap: "wrap" }}>
            <Stat label="總數" value={stats.total} />
            <Stat label="已同意（可外撥）" value={stats.consented} good />
            <Stat label="待邀請" value={stats.by_status["imported"] ?? 0} />
            <Stat label="拒絕聯繫" value={stats.by_status["do_not_contact"] ?? 0} />
            <Stat label="號碼待確認" value={stats.needs_review} />
          </div>
          <button className="ghost small" style={{ marginTop: 12 }} onClick={() => api.downloadInvitesCsv(true)}>
            ⬇ 匯出同意連結（CSV）
          </button>
          <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            匯出「名稱＋電話＋同意連結」，用簡訊／Email／QR 等合法管道邀請對方同意。
          </p>
        </div>
      )}

      {/* 名單列表 */}
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="section-title" style={{ margin: 0 }}>名單（{rows.length}）</div>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s === "" ? "全部狀態" : STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
        {callMsg && <div className="muted" style={{ marginTop: 8 }}>{callMsg}</div>}
        {loading ? (
          <div className="muted">載入中…</div>
        ) : rows.length === 0 ? (
          <p className="muted">此狀態尚無名單。</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: 13 }}>
                <th style={{ padding: "8px 4px" }}>名稱</th>
                <th>電話</th>
                <th>類別</th>
                <th>狀態</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((l) => (
                <tr key={l.id} style={{ borderTop: "1px solid var(--border)", fontSize: 14 }}>
                  <td
                    style={{ padding: "10px 4px", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    title={l.name}
                  >
                    {l.name || "—"}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {l.phone}
                    {!l.phone_valid && <span className="action stop_loss" style={{ marginLeft: 6 }}>號碼待確認</span>}
                  </td>
                  <td className="muted" style={{ whiteSpace: "nowrap" }}>{l.category || "—"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <span className={l.consent ? "action take_profit" : "muted"}>
                      {STATUS_LABEL[l.status] ?? l.status}
                    </span>
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {l.consent && l.phone_valid ? (
                      <button className="ghost small" onClick={() => doCall(l.id, l.name)}>📞 AI 致電</button>
                    ) : (
                      <a className="ghost small" href={l.invite_url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
                        看同意頁
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, good }: { label: string; value: number; good?: boolean }) {
  return (
    <div>
      <div className={good ? "action take_profit" : ""} style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
      <div className="muted" style={{ fontSize: 13 }}>{label}</div>
    </div>
  );
}
