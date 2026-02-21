import { useState, useEffect } from "react";
import api from "@/api/client";
import { RefreshCw, Trash2, Plus, LogIn, RotateCcw } from "lucide-react";

interface Account {
  id: number; site_name: string; site_url: string; username: string;
  uid: string; uploaded: number; downloaded: number; ratio: number;
  bonus: number; user_class: string; is_active: boolean;
}

// 登录弹窗的步骤
type LoginStep = "form" | "captcha" | "done";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [refreshing, setRefreshing] = useState<number | null>(null);

  // 登录流程状态
  const [loginStep, setLoginStep] = useState<LoginStep>("form");
  const [siteUrl, setSiteUrl] = useState("https://www.nicept.net");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captchaInput, setCaptchaInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [captchaImage, setCaptchaImage] = useState("");
  const [hasCaptcha, setHasCaptcha] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const load = () => api.get("/accounts/").then((r) => setAccounts(r.data));
  useEffect(() => { load(); }, []);

  const openAdd = () => {
    setLoginStep("form");
    setSiteUrl("https://www.nicept.net");
    setUsername(""); setPassword(""); setCaptchaInput("");
    setSessionId(""); setCaptchaImage(""); setLoginError("");
    setShowAdd(true);
  };

  // 第一步：获取验证码
  const handleInitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true); setLoginError("");
    try {
      const r = await api.post("/site-login/init", { site_url: siteUrl });
      setSessionId(r.data.session_id);
      setCaptchaImage(r.data.captcha_image);
      setHasCaptcha(r.data.has_captcha);
      setLoginStep("captcha");
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || "获取验证码失败");
    } finally { setLoginLoading(false); }
  };

  // 刷新验证码
  const handleRefreshCaptcha = async () => {
    setLoginLoading(true); setLoginError("");
    try {
      const r = await api.post("/site-login/refresh-captcha", { site_url: siteUrl });
      setSessionId(r.data.session_id);
      setCaptchaImage(r.data.captcha_image);
      setCaptchaInput("");
    } catch { setLoginError("刷新验证码失败"); }
    finally { setLoginLoading(false); }
  };

  // 第二步：提交登录
  const handleSubmitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true); setLoginError("");
    try {
      const r = await api.post("/site-login/submit", {
        session_id: sessionId,
        site_url: siteUrl,
        username, password,
        captcha: captchaInput,
        auto_save: true,
      });
      if (r.data.success) {
        setShowAdd(false);
        load();
      } else {
        setLoginError(r.data.message || "登录失败");
        // 登录失败重新获取验证码
        handleRefreshCaptcha();
      }
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || "登录请求失败");
    } finally { setLoginLoading(false); }
  };

  const handleRefresh = async (id: number) => {
    setRefreshing(id);
    try { await api.post(`/accounts/${id}/refresh`); await load(); }
    finally { setRefreshing(null); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此账号？")) return;
    await api.delete(`/accounts/${id}`);
    load();
  };

  const fmtSize = (bytes: number) => (bytes / 1024 / 1024 / 1024).toFixed(2) + " GB";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">PT 账号管理</h1>
        <button onClick={openAdd} className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm shadow-blue-500/20">
          <Plus size={16} /> 添加账号
        </button>
      </div>

      {/* 登录弹窗 */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md mx-4 overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500" />
            <div className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="p-2.5 rounded-xl bg-blue-100 dark:bg-blue-900/30">
                  <LogIn size={20} className="text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900 dark:text-white">
                    {loginStep === "form" ? "添加 PT 账号" : "输入验证码"}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {loginStep === "form" ? "通过模拟登录自动获取 Cookie" : "请输入图中的验证码完成登录"}
                  </p>
                </div>
              </div>

              {loginError && (
                <div className="mb-4 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded-xl text-sm text-red-600 dark:text-red-400">
                  {loginError}
                </div>
              )}

              {/* 第一步：填写账号信息 */}
              {loginStep === "form" && (
                <form onSubmit={handleInitLogin} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">站点地址</label>
                    <input value={siteUrl} onChange={(e) => setSiteUrl(e.target.value)}
                      className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">用户名</label>
                    <input value={username} onChange={(e) => setUsername(e.target.value)}
                      className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">密码</label>
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all" required />
                  </div>
                  <div className="flex gap-3 pt-1">
                    <button type="submit" disabled={loginLoading}
                      className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-60">
                      {loginLoading ? <><RefreshCw size={14} className="animate-spin" />获取验证码...</> : "下一步"}
                    </button>
                    <button type="button" onClick={() => setShowAdd(false)}
                      className="px-5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      取消
                    </button>
                  </div>
                </form>
              )}

              {/* 第二步：验证码 */}
              {loginStep === "captcha" && (
                <form onSubmit={handleSubmitLogin} className="space-y-4">
                  {hasCaptcha && captchaImage && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">验证码图片</label>
                      <div className="flex items-center gap-3">
                        <img src={captchaImage} alt="验证码"
                          className="h-12 rounded-lg border border-gray-200 dark:border-gray-700 bg-white" />
                        <button type="button" onClick={handleRefreshCaptcha} disabled={loginLoading}
                          className="p-2 rounded-lg text-gray-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors disabled:opacity-50" title="刷新验证码">
                          <RotateCcw size={16} className={loginLoading ? "animate-spin" : ""} />
                        </button>
                      </div>
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      {hasCaptcha ? "输入验证码" : "验证码（无需填写）"}
                    </label>
                    <input value={captchaInput} onChange={(e) => setCaptchaInput(e.target.value)}
                      placeholder={hasCaptcha ? "请输入图中字符" : "该站点无验证码"}
                      disabled={!hasCaptcha}
                      className="w-full bg-gray-50 dark:bg-gray-950/50 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all disabled:opacity-50" />
                  </div>
                  <div className="flex gap-3 pt-1">
                    <button type="submit" disabled={loginLoading}
                      className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-60">
                      {loginLoading ? <><RefreshCw size={14} className="animate-spin" />登录中...</> : <><LogIn size={14} />登录</>}
                    </button>
                    <button type="button" onClick={() => setLoginStep("form")}
                      className="px-5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      返回
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-6 border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow duration-300">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-lg">
                  {acc.username[0]?.toUpperCase() || 'U'}
                </div>
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white text-lg leading-tight">{acc.username}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-gray-500 dark:text-gray-400 text-xs bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">UID: {acc.uid}</span>
                    <span className="text-gray-500 dark:text-gray-400 text-xs bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">{acc.user_class}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => handleRefresh(acc.id)} disabled={refreshing === acc.id} title="刷新数据"
                  className="p-2 rounded-lg text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 transition-colors">
                  <RefreshCw size={16} className={refreshing === acc.id ? "animate-spin" : ""} />
                </button>
                <button onClick={() => handleDelete(acc.id)} title="删除账号"
                  className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-4 text-sm bg-gray-50/50 dark:bg-gray-950/50 p-4 rounded-xl border border-gray-100 dark:border-gray-800/50">
              <div><span className="text-gray-400 text-xs block mb-1">上传</span><div className="font-semibold text-gray-900 dark:text-gray-100">{fmtSize(acc.uploaded)}</div></div>
              <div><span className="text-gray-400 text-xs block mb-1">下载</span><div className="font-semibold text-gray-900 dark:text-gray-100">{fmtSize(acc.downloaded)}</div></div>
              <div><span className="text-gray-400 text-xs block mb-1">分享率</span><div className="font-semibold text-emerald-600 dark:text-emerald-400">{acc.ratio > 0 ? acc.ratio.toFixed(2) : "∞"}</div></div>
              <div><span className="text-gray-400 text-xs block mb-1">魔力</span><div className="font-semibold text-orange-600 dark:text-orange-400">{acc.bonus.toFixed(1)}</div></div>
            </div>
          </div>
        ))}
        {accounts.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-400 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 border-dashed">
            暂无账号，请点击上方按钮添加
          </div>
        )}
      </div>
    </div>
  );
}
