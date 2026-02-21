import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import {
  LayoutDashboard, User, Search, ListFilter, HardDrive,
  History, Settings, LogOut, FileText, Sun, Moon, ShieldAlert,
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "仪表盘" },
  { to: "/accounts", icon: User, label: "账号管理" },
  { to: "/torrents", icon: Search, label: "种子搜索" },
  { to: "/rules", icon: ListFilter, label: "自动规则" },
  { to: "/downloaders", icon: HardDrive, label: "下载器" },
  { to: "/history", icon: History, label: "下载历史" },
  { to: "/hr", icon: ShieldAlert, label: "H&R 考核" },
  { to: "/settings", icon: Settings, label: "系统设置" },
  { to: "/logs", icon: FileText, label: "日志" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
      {/* 侧边栏 */}
      <aside className="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col transition-colors duration-300 z-10">
        <div className="p-6 text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent border-b border-gray-100 dark:border-gray-800">
          NicePT Helper
        </div>
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                  ? "bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50 hover:text-gray-900 dark:hover:text-gray-200"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon size={18} className={`transition-colors ${isActive ? "text-blue-600 dark:text-blue-400" : "text-gray-400 dark:text-gray-500"}`} />
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-100 dark:border-gray-800 p-4 bg-gray-50/50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex flex-shrink-0 items-center justify-center text-blue-700 dark:text-blue-400 font-bold text-sm">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{user?.username}</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={toggle}
                className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                title={theme === "dark" ? "切换亮色" : "切换暗色"}
              >
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button
                onClick={logout}
                className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                title="登出"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* 主内容 */}
      <main className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300 p-8">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
