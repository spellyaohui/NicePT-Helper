import { useState, useEffect } from "react";
import api from "@/api/client";
import { Trash2, RefreshCw } from "lucide-react";

const STATUS_MAP: Record<string, string> = {
  downloading: "下载中", seeding: "做种中", completed: "已完成",
  paused: "已暂停", deleted: "已删除", expired_deleted: "过期删除",
  dynamic_deleted: "容量删除", unregistered_deleted: "下架删除",
};

const STATUS_COLOR: Record<string, string> = {
  downloading: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  seeding: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  completed: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
  paused: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  deleted: "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
};

export default function HistoryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");
  const [syncing, setSyncing] = useState(false);

  const load = () => {
    const params: any = { page, page_size: 20 };
    if (filter) params.status = filter;
    api.get("/history/", { params }).then((r) => { setItems(r.data.items); setTotal(r.data.total); });
  };
  useEffect(() => { load(); }, [page, filter]);

  const handleSync = async () => {
    setSyncing(true);
    try { await api.post("/history/sync-status"); load(); }
    finally { setSyncing(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此记录？")) return;
    await api.delete(`/history/${id}`); load();
  };

  const fmtSize = (b: number) => b ? (b / 1024 ** 3).toFixed(2) + " GB" : "-";
  const totalPages = Math.ceil(total / 20);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">下载历史</h1>
        <div className="flex gap-3">
          <select value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1); }}
            className="border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2 text-sm bg-white dark:bg-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm">
            <option value="">全部状态</option>
            {Object.entries(STATUS_MAP).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button onClick={handleSync} disabled={syncing}
            className="flex items-center gap-2 bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-sm disabled:opacity-50">
            <RefreshCw size={16} className={syncing ? "animate-spin text-blue-500" : "text-gray-500 dark:text-gray-400"} /> 同步状态
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm overflow-hidden border border-gray-100 dark:border-gray-800">
        {items.length === 0 ? (
          <div className="p-5 text-gray-400 text-sm text-center">暂无记录</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50/50 dark:bg-gray-950/50 text-gray-500 dark:text-gray-400">
              <tr className="border-b border-gray-100 dark:border-gray-800 border-solid">
                <th className="text-left px-5 py-3 font-medium">标题</th>
                <th className="text-right px-4 py-3 font-medium">大小</th>
                <th className="text-left px-4 py-3 font-medium">状态</th>
                <th className="text-left px-4 py-3 font-medium">促销</th>
                <th className="text-left px-4 py-3 font-medium">时间</th>
                <th className="px-5 py-3 font-medium w-16"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((h: any) => (
                <tr key={h.id} className="border-b border-gray-50 dark:border-gray-800 last:border-0 hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-4 max-w-md">
                    <div className="truncate font-medium text-gray-900 dark:text-gray-100" title={h.title || h.torrent_id}>
                      {h.title || h.torrent_id}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right whitespace-nowrap text-gray-500 dark:text-gray-400 font-medium">{fmtSize(h.size)}</td>
                  <td className="px-4 py-4">
                    <span className={`px-2.5 py-1 rounded-md text-xs font-medium ${STATUS_COLOR[h.status] || "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}>
                      {STATUS_MAP[h.status] || h.status}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-xs font-medium text-gray-500 dark:text-gray-400">
                    {h.discount_type ? (
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold tracking-wider bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 uppercase">
                        {h.discount_type}
                      </span>
                    ) : "-"}
                  </td>
                  <td className="px-4 py-4 text-gray-400 dark:text-gray-500 whitespace-nowrap text-xs">{h.created_at?.slice(0, 16)}</td>
                  <td className="px-5 py-4 text-right">
                    <button onClick={() => handleDelete(h.id)} title="删除记录"
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors inline-flex">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
