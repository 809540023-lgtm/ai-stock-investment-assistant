import { FormEvent, useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, name);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="card auth-box">
        <h1 className="page-title center">林博台股AI 投資助理</h1>
        <p className="page-sub center">
          針對單一股票，建立「完整分析」與「每月投入」兩種個人化投資計畫
        </p>
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <label>暱稱</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="你的名字" />
            </>
          )}
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <label>密碼</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="至少 6 碼"
            required
          />
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={busy} style={{ width: "100%", marginTop: 16 }}>
            {busy ? "處理中…" : mode === "login" ? "登入" : "註冊並登入"}
          </button>
        </form>
        <p className="center muted" style={{ marginTop: 16 }}>
          {mode === "login" ? "還沒有帳號？" : "已經有帳號？"}{" "}
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "註冊新帳號" : "改用登入"}
          </a>
        </p>
      </div>
    </div>
  );
}
