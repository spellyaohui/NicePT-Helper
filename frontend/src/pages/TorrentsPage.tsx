import { useState, useEffect } from "react";
import api from "@/api/client";
import { Search, Download, AlertTriangle, Clock } from "lucide-react";

interface Torrent {
  id: string; title: string; subtitle: string; category: string;
  size: number; seeders: number; leechers: number; completions: number;
  discount_type: string; discount_end_time: string;
  is_free: boolean; has_hr: boolean;
  download_status: string; download_progress: number;
  detail_url: string; download_url: string;
}

interface Category { id: number; name: string; }

export default function TorrentsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [results, setResults] = useState<Torrent[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    account_id: 0, keyword: "", category: 0, spstate: 0, incldead: 0,
  });

  useEffect(() => {
    api.get("/accounts/").then((r) => {
      setAccounts(r.data);
      if (r.data.length > 0) setForm((f) => ({ ...f, account_id: r.data[0].id }));
    });
    api.get("/torrents/categories").then((r) => setCategories(r.data));
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try { const r = await api.post("/torrents/search", form); setResults(r.data); }
    finally { setLoading(false); }
  };

  const fmtSize = (b: number) => {
    if (b >= 1024 ** 3) return (b / 1024 ** 3).toFixed(2) + " GB";
    if (b >= 1024 ** 2) return (b / 1024 ** 2).toFixed(1) + " MB";
    return (b / 1024).toFixed(0) + " KB";
  };

  const discountBadge = (t: Torrent) => {
    if (!t.discount_type) return null;
    const colors: Record<string, string> = {
      free: "bg-green-100 text-green-700 border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700",
      twoupfree: "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-700",
      twoup: "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700",
      halfdown: "bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700",
    };
    const labels: Record<string, string> = {
      free: "免费", twoupfree: "2X免费", twoup: "2X上传",
      halfdown: "50%", thirtypercent: "30%", custom: "自定义",
    };
    const cls = colors[t.discount_type] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
    return <span className={`px-1.5 py-0.5 rounded text-xs border ${cls}`}>{labels[t.discount_type] || t.discount_type}</span>;
  };

  const statusBadge = (t: Torrent) => {
    if (!t.download_status) return null;
    const map: Record<string, [string, string]> = {
      seeding: ["做种中", "bg-green-500"], downloading: ["下载中", "bg-blue-500"], completed: ["已完成", "bg-gray-400"],
    };
    const [label, color] = map[t.download_status] || [t.download_status, "bg-gray-400"];
    return (
      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs text-white ${color}`}>
        {label}{t.download_progress > 0 && t.download_progress < 100 && ` ${t.download_progress.toFixed(0)}%`}
      </span>
    );
  };

  const freeTimeLeft = (t: Torrent) => {
    if (!t.discount_end_time) return null;
    const diff = new Date(t.discount_end_time).getTime() - Date.now();
    if (diff <= 0) return <span className="text-xs text-red-400">已过期</span>;
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(hours / 24);
    const text = days > 0 ? `${days}天${hours % 24}时` : `${hours}时`;
    return (
      <span className={`inline-flex items-center gap-0.5 text-xs ${hours < 24 ? "text-red-500 font-medium" : "text-gray-400"}`}>
        <Clock size={10} />{text}
      </span>
    );
  };

  const inputCls = "border dark:border-gray-600 rounded px-3 py-1.5 text-sm dark:bg-gray-700 dark:text-white";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">种子搜索</h1>

      <form onSubmit={handleSearch} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-5 mb-6 border border-gray-100 dark:border-gray-800">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">账号</label>
            <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: +e.target.value })} className={inputCls}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.username}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">关键词</label>
            <input value={form.keyword} onChange={(e) => setForm({ ...form, keyword: e.target.value })}
              className={`w-full ${inputCls}`} placeholder="搜索种子..." />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">分类</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: +e.target.value })} className={`${inputCls} min-w-[120px]`}>
              <option value={0}>全部</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">促销</label>
            <select value={form.spstate} onChange={(e) => setForm({ ...form, spstate: +e.target.value })} className={`${inputCls} min-w-[120px]`}>
              <option value={0}>全部</option>
              <option value={2}>免费</option>
              <option value={3}>2X上传</option>
              <option value={4}>2X免费</option>
            </select>
          </div>
          <button type="submit" disabled={loading}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm shadow-blue-500/20 disabled:opacity-50">
            <Search size={16} /> {loading ? "搜索中..." : "搜索"}
          </button>
        </div>
      </form>

      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm overflow-hidden border border-gray-100 dark:border-gray-800">
        {results.length === 0 ? (
          <div className="p-12 text-gray-400 text-sm text-center bg-gray-50/50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-800">{loading ? "正在拼命搜索中..." : "输入条件后点击搜索"}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50/80 dark:bg-gray-950/80 text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">标题</th>
                  <th className="text-left px-4 py-3 font-medium">状态</th>
                  <th className="text-right px-4 py-3 font-medium">大小</th>
                  <th className="text-right px-4 py-3 font-medium">做种</th>
                  <th className="text-right px-4 py-3 font-medium">下载</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {results.map((t) => (
                  <tr key={t.id} className={`border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${t.download_status ? "bg-blue-50/30 dark:bg-blue-900/10" : "bg-white dark:bg-gray-900"}`}>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="font-semibold text-gray-900 dark:text-gray-100 break-words">{t.title}</span>
                        {t.has_hr && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-red-100 text-red-600 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700/50 font-bold shrink-0 uppercase"
                            title="H&R: 下载后必须做种达标，否则可能被封号">
                            <AlertTriangle size={10} />H&R
                          </span>
                        )}
                      </div>
                      {t.subtitle && <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 max-w-2xl">{t.subtitle}</div>}
                      <div className="flex items-center gap-2 mt-2">{discountBadge(t)}{freeTimeLeft(t)}{statusBadge(t)}</div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      {t.download_status ? (
                        <span className={`text-xs font-medium px-2 py-1 rounded-md ${t.download_status === "seeding" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : t.download_status === "downloading" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}>
                          {t.download_status === "seeding" ? "做种中" : t.download_status === "downloading" ? `下载 ${t.download_progress}%` : "已完成"}
                        </span>
                      ) : <span className="text-xs text-gray-400 dark:text-gray-500">未下载</span>}
                    </td>
                    <td className="px-4 py-4 text-right whitespace-nowrap text-gray-700 dark:text-gray-300 font-medium">{fmtSize(t.size)}</td>
                    <td className="px-4 py-4 text-right text-green-600 dark:text-green-400 font-semibold">{t.seeders}</td>
                    <td className="px-4 py-4 text-right text-red-500 dark:text-red-400 font-semibold">{t.leechers}</td>
                    <td className="px-4 py-4 text-center">
                      <a href={t.download_url} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center p-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-blue-600 hover:text-white dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-blue-600 dark:hover:text-white transition-colors" title="下载种子">
                        <Download size={16} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {results.length > 0 && (
          <div className="px-5 py-3 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-900/50">
            <span>共 <strong className="text-gray-900 dark:text-gray-200">{results.length}</strong> 条结果</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-400"></span>H&R: {results.filter(t => t.has_hr).length}</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-400"></span>免费: {results.filter(t => t.is_free).length}</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-400"></span>已下载: {results.filter(t => !!t.download_status).length}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
