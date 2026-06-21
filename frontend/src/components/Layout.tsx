import { ReactNode, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const [unread, setUnread] = useState(0);
  const [theme, setTheme] = useState<string>(
    () => localStorage.getItem("ai_invest_theme") || "dark"
  );
  const location = useLocation();

  useEffect(() => {
    api
      .reminders(true)
      .then((r) => setUnread(r.length))
      .catch(() => setUnread(0));
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ai_invest_theme", theme);
  }, [theme]);

  const link = (to: string, label: string, badge?: number) => (
    <NavLink
      to={to}
      className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
    >
      <span>{label}</span>
      {badge ? <span className="badge">{badge}</span> : null}
    </NavLink>
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          林博台股AI 投資助理
          <small>單股分析 ・ 零存整付</small>
        </div>
        {link("/dashboard", "投資總覽")}
        {link("/create", "＋ 建立投資計畫")}
        {link("/plans", "我的投資計畫")}
        {link("/watchlist", "觀察清單")}
        {link("/compare", "個股比較")}
        {link("/reminders", "提醒中心", unread)}
        <div className="sidebar-footer">
          <button
            className="ghost small"
            style={{ marginBottom: 10, width: "100%" }}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "☀️ 淺色模式" : "🌙 深色模式"}
          </button>
          <div className="muted">{user?.name}</div>
          <div className="muted" style={{ fontSize: 12 }}>{user?.email}</div>
          <button className="ghost small" style={{ marginTop: 10 }} onClick={logout}>
            登出
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
