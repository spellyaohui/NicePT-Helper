import { useState, useEffect } from "react";
import api from "@/api/client";
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, ShieldOff, Trash2, Zap } from "lucide-react";

interface HRItem {
  id: number; hr_id: number;
  torrent_id: string; torrent_name: string;
  uploaded: number; downloaded: number; share_ratio: number;
  seed_time_required: string; completed_at: string;
  inspect_time_left: string; comment: string;
  status: string; account_id: number; updated_at: string;
}

const STATUS_MAP: Record<string, { label: string; color: string; icon: any }> = {
  inspecting: { label: "考核中", color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400", icon: AlertTriangle },
  reached: { label: "已达标", color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", icon: CheckCircle },
  unreached: { label: "未达标", color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", icon: XCircle },
  pardoned: { label: "已豁免", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", icon: ShieldOff },
};

const fmtSize = (b: number) => {
  if (!b) return "0";
  if (b >= 1024 ** 4) return (b / 1024 ** 4).toFixed(2) + " TB";
  if (b >= 1024 ** 3) return (b / 1024 ** 3).toFixed(2) + " GB";
  if (b >= 1024 ** 2) return (b / 1024 ** 2).toFixed(2) + " MB";
  if (b >= 1024) return (b / 1024).toFixed(2) + " KB";
  return b + " B";
};

const fmtRatio = (r: number) => {
  if (r === Infinity || r > 999999) return "∞";
  return r.toFixed(3);
};

export default function HRPage() {
  const [items, setItems] = useState<HRItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("inspecting");
  const [syncing, setSyncing] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [accountId, setAccountId] = useState<number>(0);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [confirmHrId, setConfirmHrId] = useState<number | null>(null);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    api.get("/accounts/").then((r) => {
      const list = r.data || [];
      setAccounts(list);
      if (list.length > 0 && !accountId) setAccountId(list[0].id);
    });
  }, []);

  const load = () => {
    api.get("/hr/", { params: { status: filter, page, page_size: 50 } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total); });
    api.get("/hr/summary").then((r) => setSummary(r.data));
  };

  useEffect(() => { load(); }, [page, filter]);

  const handleSync = async () => {
    if (!accountId) return;
    setSyncing(true);
    try {
      // 同时刷新账号数据 + 同步 H&R 记录
      await Promise.all([
        api.post(`/accounts/${accountId}/refresh`),
        api.post("/hr/sync", null, { params: { account_id: accountId } }),
      ]);
      load();
    } finally { setSyncing(false); }
  };

  const handleRemove = async (hrId: number) => {
    if (!accountId) return;
    setConfirmHrId(hrId);
  };

  const doRemove = async () => {
    if (confirmHrId === null || !accountId) return;
    setRemoving(true);
    try {
      const r = await api.post(`/hr/remove/${confirmHrId}`, null, { params: { account_id: accountId } });
      setConfirmHrId(null);
      if (r.data.success) load();
      else alert(r.data.message || "消除失败");
    } catch { alert("请求失败"); }
    finally { setRemoving(false); }
  };

  const totalPages = Math.ceil(total / 50);

  return (
    <div>
      {/* 魔力消除确认弹窗 */}
      {confirmHrId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-sm mx-4 overflow-hidden">
            {/* 顶部警示色条 */}
            <div className="h-1.5 bg-gradient-to-r from-amber-400 to-orange-500" />
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 rounded-xl bg-amber-100 dark:bg-amber-900/30">
                  <Zap size={22} className="text-amber-500 dark:text-amber-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900 dark:text-white">确认消除 H&R</h3>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">此操作不可撤销</p>
                </div>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-xl px-4 py-3 mb-5">
                <p className="text-sm text-amber-800 dark:text-amber-300 font-medium">
                  消除此 H&R 将扣除
                  <span className="text-amber-600 dark:text-amber-400 font-bold text-base mx-1">20,000</span>
                  魔力值
                </p>
                <p className="text-xs text-amber-600 dark:text-amber-500 mt-1">请确认您的账号有足够魔力后再操作</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setConfirmHrId(null)}
                  disabled={removing}
                  className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50">
                  取消
                </button>
                <button
                  onClick={doRemove}
                  disabled={removing}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white text-sm font-medium transition-all shadow-sm disabled:opacity-60 flex items-center justify-center gap-2">
                  {removing ? (
                    <><RefreshCw size={14} className="animate-spin" />处理中...</>
                  ) : (
                    <><Zap size={14} />确认消除</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">H&R 考核</h1>
        <div className="flex gap-3 items-center">
          {accounts.length > 1 && (
            <select value={accountId} onChange={(e) => setAccountId(+e.target.value)}
              className="border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2 text-sm bg-white dark:bg-gray-800 dark:text-gray-200 outline-none shadow-sm">
              {accounts.map((a: any) => <option key={a.id} value={a.id}>{a.username}</option>)}
            </select>
          )}
          <button onClick={handleSync} disabled={syncing || !accountId}
            className="flex items-center gap-2 bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-50">
            <RefreshCw size={16} className={syncing ? "animate-spin text-blue-500" : "text-gray-500 dark:text-gray-400"} />
            从站点同步
          </button>
        </div>
      </div>

      {/* 状态统计卡片 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {Object.entries(STATUS_MAP).map(([key, { label, color, icon: Icon }]) => (
          <button key={key} onClick={() => { setFilter(key); setPage(1); }}
            className={`flex items-center gap-3 p-4 rounded-2xl border transition-all shadow-sm ${
              filter === key
                ? "border-blue-400 dark:border-blue-500 bg-blue-50/50 dark:bg-blue-900/20 ring-1 ring-blue-400/30"
                : "border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-200 dark:hover:border-gray-700"
            }`}>
            <div className={`p-2 rounded-lg ${color}`}><Icon size={18} /></div>
            <div className="text-left">
              <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">{summary[key] || 0}</div>
            </div>
          </button>
        ))}
      </div>

      {/* 表格 */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm overflow-hidden border border-gray-100 dark:border-gray-800">
        {items.length === 0 ? (
          <div className="p-8 text-gray-400 text-sm text-center">暂无 H&R 记录，点击"从站点同步"获取数据</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50/50 dark:bg-gray-950/50 text-gray-500 dark:text-gray-400">
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <th className="text-center px-3 py-3 font-medium w-16">#</th>
                  <th className="text-left px-4 py-3 font-medium">种子</th>
                  <th className="text-right px-3 py-3 font-medium">上传</th>
                  <th className="text-right px-3 py-3 font-medium">下载</th>
                  <th className="text-right px-3 py-3 font-medium">分享率</th>
                  <th className="text-center px-3 py-3 font-medium">需做种</th>
                  <th className="text-center px-3 py-3 font-medium">完成时间</th>
                  <th className="text-center px-3 py-3 font-medium">剩余时间</th>
                  <th className="text-left px-3 py-3 font-medium">备注</th>
                  <th className="text-center px-3 py-3 font-medium w-16">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((h) => {
                  const st = STATUS_MAP[h.status] || STATUS_MAP.inspecting;
                  return (
                    <tr key={h.id} className="border-b border-gray-50 dark:border-gray-800 last:border-0 hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors">
                      <td className="px-3 py-3 text-center text-gray-400 font-mono text-xs">{h.hr_id}</td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="truncate font-medium text-gray-900 dark:text-gray-100" title={h.torrent_name}>
                          {h.torrent_name || h.torrent_id}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-right whitespace-nowrap text-green-600 dark:text-green-400 font-medium text-xs">{fmtSize(h.uploaded)}</td>
                      <td className="px-3 py-3 text-right whitespace-nowrap text-red-500 dark:text-red-400 font-medium text-xs">{fmtSize(h.downloaded)}</td>
                      <td className="px-3 py-3 text-right whitespace-nowrap font-medium text-xs">{fmtRatio(h.share_ratio)}</td>
                      <td className="px-3 py-3 text-center whitespace-nowrap text-xs text-gray-600 dark:text-gray-300">{h.seed_time_required || "---"}</td>
                      <td className="px-3 py-3 text-center whitespace-nowrap text-xs text-gray-400">{h.completed_at || "---"}</td>
                      <td className="px-3 py-3 text-center whitespace-nowrap">
                        <span className={`text-xs font-medium ${h.status === "inspecting" ? "text-yellow-600 dark:text-yellow-400" : "text-gray-400"}`}>
                          {h.inspect_time_left || "---"}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-xs text-gray-400 max-w-[120px] truncate" title={h.comment}>{h.comment || "-"}</td>
                      <td className="px-3 py-3 text-center">
                        {(h.status === "inspecting" || h.status === "unreached") && (
                          <button onClick={() => handleRemove(h.hr_id)} title="消除 H&R（扣 20000 魔力）"
                            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors inline-flex">
                            <Trash2 size={15} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-800 text-sm bg-gray-50/50 dark:bg-gray-950/50">
            <span className="text-gray-500 dark:text-gray-400">共 <strong className="text-gray-900 dark:text-gray-200">{total}</strong> 条</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}
                className="px-4 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium">
                上一页
              </button>
              <span className="px-4 py-1.5 font-medium text-gray-700 dark:text-gray-300">{page} / {totalPages}</span>
              <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages}
                className="px-4 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium">
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
