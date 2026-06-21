import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import CreatePlan from "./pages/CreatePlan";
import FullAnalysisForm from "./pages/FullAnalysisForm";
import RecurringForm from "./pages/RecurringForm";
import PlanResult from "./pages/PlanResult";
import MyPlans from "./pages/MyPlans";
import UpdateRecords from "./pages/UpdateRecords";
import Reminders from "./pages/Reminders";
import Watchlist from "./pages/Watchlist";
import Compare from "./pages/Compare";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="auth-wrap">載入中…</div>;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/create" element={<CreatePlan />} />
        <Route path="/create/full" element={<FullAnalysisForm />} />
        <Route path="/create/recurring" element={<RecurringForm />} />
        <Route path="/plans" element={<MyPlans />} />
        <Route path="/plans/:id" element={<PlanResult />} />
        <Route path="/plans/:id/updates" element={<UpdateRecords />} />
        <Route path="/watchlist" element={<Watchlist />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/reminders" element={<Reminders />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}
