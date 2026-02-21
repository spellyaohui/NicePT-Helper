import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import AccountsPage from "@/pages/AccountsPage";
import TorrentsPage from "@/pages/TorrentsPage";
import RulesPage from "@/pages/RulesPage";
import DownloadersPage from "@/pages/DownloadersPage";
import HistoryPage from "@/pages/HistoryPage";
import HRPage from "@/pages/HRPage";
import SettingsPage from "@/pages/SettingsPage";
import LogsPage from "@/pages/LogsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen dark:bg-gray-950 dark:text-gray-400">加载中...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="torrents" element={<TorrentsPage />} />
          <Route path="rules" element={<RulesPage />} />
          <Route path="downloaders" element={<DownloadersPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="hr" element={<HRPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="logs" element={<LogsPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
