import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/api/client";

export default function LoginPage() {
  const { login, register, token } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) { navigate("/"); return; }
    api.get("/auth/check-init").then((r) => {
      setIsRegister(!r.data.initialized);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) await register(username, password);
      else await login(username, password);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "操作失败");
    }
  };

  if (loading) return <div className="flex items-center justify-center h-screen dark:text-gray-400">加载中...</div>;

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-300 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-500/20 dark:bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-indigo-500/20 dark:bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>

      <form onSubmit={handleSubmit} className="relative bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border border-white/20 dark:border-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-md mx-4 transition-all duration-300">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-extrabold bg-gradient-to-br from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent tracking-tight">
            {isRegister ? "初始化管理员" : "NicePT Helper"}
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-2">
            {isRegister ? "设置您的初始管理员账号" : "欢迎回来，请登录您的账号"}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20 text-red-600 dark:text-red-400 text-sm p-3.5 rounded-xl mb-6 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 flex-shrink-0">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">用户名</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 dark:focus:ring-blue-500/40 transition-all duration-200" required placeholder="请输入用户名" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">密码</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 dark:focus:ring-blue-500/40 transition-all duration-200" required placeholder="请输入密码" />
          </div>
          <button type="submit"
            className="w-full relative overflow-hidden group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-3 rounded-xl font-medium shadow-lg shadow-blue-500/30 dark:shadow-blue-900/20 transition-all duration-200 active:scale-[0.98]">
            <span className="relative z-10">{isRegister ? "创建管理员" : "登录"}</span>
            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
          </button>
        </div>
      </form>
    </div>
  );
}
