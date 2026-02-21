import { useState, useEffect } from "react";
import api from "@/api/client";
import { Plus, Trash2, Wifi, WifiOff } from "lucide-react";

interface DL {
  id: number; name: string; type: string; host: string; port: number;
  username: string; use_ssl: boolean; is_default: boolean;
}

const emptyForm = {
  name: "", type: "qbittorrent", host: "127.0.0.1", port: 8080,
  username: "", password: "", use_ssl: false, is_default: false,
};

export default function DownloadersPage() {
  const [dls, setDls] = useState<DL[]>([]);
  const [stats, setStats] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState("");

  const load = () => {
    api.get("/downloaders/").then((r) => setDls(r.data));
    api.get("/downloaders/stats").then((r) => setStats(r.data));
  };
  useEffect(() => { load(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/downloaders/", { ...form, port: +form.port });
    setShowForm(false); setForm(emptyForm); load();
  };

  const handleTest = async () => {
    setTesting(true); setTestMsg("");
    try { const r = await api.post("/downloaders/test", { ...form, port: +form.port }); setTestMsg(r.data.message); }
    catch { setTestMsg("连接失败"); }
    finally { setTesting(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await api.delete(`/downloaders/${id}`); load();
  };

  const fmtSpeed = (b: number) => (b / 1024 / 1024).toFixed(1) + " MB/s";
  const inputCls = "w-full border dark:border-gray-600 rounded px-3 py-1.5 text-sm dark:bg-gray-700 dark:text-white";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">下载器管理</h1>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm shadow-blue-500/20">
          <Plus size={16} /> 添加下载器
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-6 mb-6 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">名称</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} required />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">类型</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className={inputCls}>
                <option value="qbittorrent">qBittorrent</option>
                <option value="transmission">Transmission</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">主机</label>
              <input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} className={inputCls} required />
            </div>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">端口</label>
              <input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: +e.target.value })} className={inputCls} required />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">用户名</label>
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">密码</label>
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputCls} />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 text-sm dark:text-gray-300">
                <input type="checkbox" checked={form.use_ssl} onChange={(e) => setForm({ ...form, use_ssl: e.target.checked })} /> SSL
              </label>
            </div>
          </div>
          <div className="flex gap-3 items-center pt-2">
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm shadow-blue-500/20">保存</button>
            <button type="button" onClick={handleTest} disabled={testing} className="bg-slate-600 hover:bg-slate-700 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {testing ? "测试中..." : "测试连接"}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 px-5 py-2 rounded-xl text-sm font-medium transition-colors">取消</button>
            {testMsg && <span className={`text-sm font-medium ${testMsg.includes("成功") ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>{testMsg}</span>}
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {dls.map((dl) => {
          const s = stats.find((x: any) => x.id === dl.id);
          return (
            <div key={dl.id} className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-6 border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl ${s?.online ? 'bg-green-50 dark:bg-green-900/20 text-green-500' : 'bg-red-50 dark:bg-red-900/20 text-red-500'}`}>
                    {s?.online ? <Wifi size={18} /> : <WifiOff size={18} />}
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white text-lg leading-tight">{dl.name}</div>
                    <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-0.5 uppercase tracking-wider">{dl.type}</div>
                  </div>
                </div>
                <button onClick={() => handleDelete(dl.id)} title="删除下载器"
                  className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-4 px-3 py-1.5 bg-gray-50 dark:bg-gray-950/50 rounded-lg border border-gray-100 dark:border-gray-800/50 inline-block">{dl.host}:{dl.port}</div>
              {s?.online && (
                <div className="grid grid-cols-2 gap-3 text-sm bg-gray-50/50 dark:bg-gray-950/50 p-4 rounded-xl border border-gray-100 dark:border-gray-800/50">
                  <div><span className="text-gray-400 text-xs block mb-1">下载速度</span><div className="font-semibold text-blue-600 dark:text-blue-400">↓ {fmtSpeed(s.download_speed)}</div></div>
                  <div><span className="text-gray-400 text-xs block mb-1">上传速度</span><div className="font-semibold text-green-600 dark:text-green-400">↑ {fmtSpeed(s.upload_speed)}</div></div>
                  <div><span className="text-gray-400 text-xs block mb-1">下载中</span><div className="font-semibold text-gray-900 dark:text-gray-100">{s.downloading_count}</div></div>
                  <div><span className="text-gray-400 text-xs block mb-1">做种中</span><div className="font-semibold text-gray-900 dark:text-gray-100">{s.seeding_count}</div></div>
                </div>
              )}
            </div>
          );
        })}
        {dls.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-400 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 border-dashed">
            暂无下载器，请点击上方按钮添加
          </div>
        )}
      </div>
    </div>
  );
}
