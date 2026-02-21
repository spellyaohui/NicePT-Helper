import { useState, useEffect, useCallback } from "react";
import api from "@/api/client";
import {
  Activity, Upload, Download, TrendingUp, AlertTriangle,
  HardDrive, RefreshCw, BarChart3, Zap,
} from "lucide-react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useTheme } from "@/contexts/ThemeContext";

interface AccountStats {
  id: number; username: string; uploaded: number; downloaded: number;
  ratio: number; bonus: number; user_class: string;
  uploaded_gb: number; downloaded_gb: number; last_refresh: string | null;
}

interface DLStats {
  id: number; name: string; type: string; online: boolean;
  download_speed?: number; upload_speed?: number;
  downloading_count?: number; seeding_count?: number;
  free_space?: number; free_space_gb?: number;
}

interface HistoryItem {
  id: number; title: string; size: number; status: string;
  discount_type: string; has_hr: boolean; discount_end_time: string | null;
  created_at: string; torrent_id: string;
}

interface DashboardData {
  accounts: number;
  rules: { total: number; enabled: number };
  downloaders: number;
  history: { total: number; downloading: number; seeding: number };
  recent_downloads: HistoryItem[];
}

interface TrendPoint {
  time: string;
  uploaded_gb: number;
  downloaded_gb: number;
  upload_speed_mbps: number;
  download_speed_mbps: number;
}

export default function DashboardPage() {
  const { theme } = useTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [accountStats, setAccountStats] = useState<AccountStats[]>([]);
  const [dlStats, setDlStats] = useState<DLStats[]>([]);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [now, setNow] = useState(new Date());
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [dash, accs, dls, trend] = await Promise.all([
        api.get("/dashboard/"),
        api.get("/accounts/"),
        api.get("/dashboard/downloader-stats"),
        api.get("/dashboard/stats-trend", { params: { hours: 24 } }),
      ]);
      setData(dash.data);
      setAccountStats(accs.data);
      setDlStats(dls.data);
      setTrendData(trend.data.points || []);
    } catch { }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (!data) return <div className="text-gray-500 dark:text-gray-400">加载中...</div>;

  const totalUp = accountStats.reduce((s, a) => s + (a.uploaded || 0), 0);
  const totalDown = accountStats.reduce((s, a) => s + (a.downloaded || 0), 0);
  const totalRatio = totalDown > 0 ? totalUp / totalDown : 0;
  const hrCount = data.recent_downloads.filter((d) => d.has_hr).length;
  const onlineDL = dlStats.find((d) => d.online);
  const freeGB = onlineDL?.free_space_gb || 0;

  const fmtBytes = (b: number) => {
    if (b >= 1024 ** 4) return (b / 1024 ** 4).toFixed(2) + " TB";
    if (b >= 1024 ** 3) return (b / 1024 ** 3).toFixed(2) + " GB";
    return (b / 1024 ** 2).toFixed(1) + " MB";
  };

  const fmtSpeed = (b: number) => {
    if (b >= 1024 ** 2) return (b / 1024 ** 2).toFixed(1) + " MB/s";
    if (b >= 1024) return (b / 1024).toFixed(1) + " KB/s";
    return b + " B/s";
  };

  const timeStr = now.toLocaleString("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });

  // 图表颜色
  const isDark = theme === "dark";
  const gridColor = isDark ? "#374151" : "#e5e7eb";
  const textColor = isDark ? "#9ca3af" : "#6b7280";

  return (
    <div className="space-y-5">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold dark:text-white">NicePT Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{timeStr}</p>
        </div>
        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-blue-500 disabled:opacity-50">
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} /> 刷新
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard icon={Activity} color="blue" label="种子数"
          value={`${data.history.seeding + data.history.downloading}`}
          sub={`${data.history.seeding} 做种 / ${data.history.downloading} 下载`} />
        <StatCard icon={Upload} color="green" label="总上传" value={fmtBytes(totalUp)} />
        <StatCard icon={Download} color="purple" label="总下载" value={fmtBytes(totalDown)} />
        <StatCard icon={TrendingUp} color="orange" label="总分享率"
          value={totalRatio > 0 ? totalRatio.toFixed(2) : "∞"} />
        <StatCard icon={AlertTriangle} color="red" label="H&R 种子"
          value={String(hrCount)} sub={hrCount > 0 ? "注意达标" : "无风险"} />
        <StatCard icon={HardDrive} color="cyan" label="磁盘可用"
          value={`${freeGB} GB`} sub={onlineDL ? onlineDL.name : "无在线下载器"} />
      </div>

      {/* 趋势图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 上传趋势 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-blue-500" />
              <span className="font-medium text-sm dark:text-white">上传趋势</span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
              {trendData.length} 个数据点
            </span>
          </div>
          <div className="h-52">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="uploadGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: textColor }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: textColor }} unit=" GB" width={60} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: isDark ? "#1f2937" : "#fff",
                      border: `1px solid ${isDark ? "#374151" : "#e5e7eb"}`,
                      borderRadius: 8, fontSize: 12,
                      color: isDark ? "#e5e7eb" : "#111",
                    }}
                    formatter={(value: number | undefined) => [`${value ?? 0} GB`, "累计上传"]}
                  />
                  <Area type="monotone" dataKey="uploaded_gb" stroke="#6366f1" strokeWidth={2}
                    fill="url(#uploadGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                暂无趋势数据，系统每10分钟采集一次
              </div>
            )}
          </div>
        </div>

        {/* 上传速率 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-cyan-500" />
              <span className="font-medium text-sm dark:text-white">上传速率</span>
            </div>
          </div>
          <div className="h-52">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: textColor }} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: textColor }} unit=" MB/s" width={65} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: isDark ? "#1f2937" : "#fff",
                      border: `1px solid ${isDark ? "#374151" : "#e5e7eb"}`,
                      borderRadius: 8, fontSize: 12,
                      color: isDark ? "#e5e7eb" : "#111",
                    }}
                    formatter={(value: number | undefined) => [`${value ?? 0} MB/s`, "上传速率"]}
                  />
                  <Line type="monotone" dataKey="upload_speed_mbps" stroke="#06b6d4" strokeWidth={2}
                    dot={false} activeDot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                暂无速率数据，系统每10分钟采集一次
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 下载器状态 */}
      {dlStats.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {dlStats.map((dl) => (
            <div key={dl.id} className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${dl.online ? "bg-green-400" : "bg-red-400"}`} />
                  <span className="font-medium text-sm dark:text-white">{dl.name}</span>
                  <span className="text-xs text-gray-400">{dl.type}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${dl.online ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"}`}>
                  {dl.online ? "在线" : "离线"}
                </span>
              </div>
              {dl.online && (
                <div className="grid grid-cols-4 gap-3 text-sm">
                  <div>
                    <div className="text-gray-400 text-xs">下载速度</div>
                    <div className="font-medium text-blue-600 dark:text-blue-400">↓ {fmtSpeed(dl.download_speed || 0)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">上传速度</div>
                    <div className="font-medium text-green-600 dark:text-green-400">↑ {fmtSpeed(dl.upload_speed || 0)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">下载中</div>
                    <div className="font-medium">{dl.downloading_count}</div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs">做种中</div>
                    <div className="font-medium">{dl.seeding_count}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 种子详情表格 */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-900/50">
          <span className="font-semibold text-gray-900 dark:text-white">近期下载记录</span>
          <span className="text-xs font-medium bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-500 dark:text-gray-400">共 {data.recent_downloads.length} 条</span>
        </div>
        {data.recent_downloads.length === 0 ? (
          <div className="p-12 text-center text-gray-400 text-sm">暂无近期下载记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-gray-500 dark:text-gray-400 text-xs border-b border-gray-100 dark:border-gray-800">
                <tr>
                  <th className="text-left px-4 py-2.5">名称</th>
                  <th className="text-right px-3 py-2.5">大小</th>
                  <th className="text-center px-3 py-2.5">H&R</th>
                  <th className="text-left px-3 py-2.5">促销</th>
                  <th className="text-left px-3 py-2.5">状态</th>
                  <th className="text-left px-3 py-2.5">时间</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_downloads.map((d) => (
                  <tr key={d.id} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition">
                    <td className="px-4 py-2.5 max-w-xs truncate font-medium dark:text-gray-200">
                      {d.title || d.torrent_id}
                    </td>
                    <td className="px-3 py-2.5 text-right whitespace-nowrap text-gray-500 dark:text-gray-400">
                      {fmtBytes(d.size)}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {d.has_hr ? (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 font-medium">
                          <AlertTriangle size={10} /> H&R
                        </span>
                      ) : (
                        <span className="text-xs text-gray-300 dark:text-gray-600">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {d.discount_type ? (
                        <span className="px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          {d.discount_type}
                        </span>
                      ) : <span className="text-xs text-gray-300 dark:text-gray-600">-</span>}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={d.status} /></td>
                    <td className="px-3 py-2.5 text-xs text-gray-400 whitespace-nowrap">{d.created_at?.slice(0, 16)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, color, label, value, sub }: {
  icon: any; color: string; label: string; value: string; sub?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400",
    green: "bg-green-50 text-green-600 dark:bg-green-500/10 dark:text-green-400",
    purple: "bg-purple-50 text-purple-600 dark:bg-purple-500/10 dark:text-purple-400",
    orange: "bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400",
    red: "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400",
    cyan: "bg-cyan-50 text-cyan-600 dark:bg-cyan-500/10 dark:text-cyan-400",
  };
  return (
    <div className="bg-white dark:bg-gray-900 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md dark:hover:border-gray-700 transition-all duration-300">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-xl flex items-center justify-center ${colorMap[color]}`}><Icon size={18} /></div>
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      {sub && <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    downloading: ["下载中", "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"],
    seeding: ["做种中", "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"],
    completed: ["已完成", "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"],
    paused: ["已暂停", "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"],
    deleted: ["已删除", "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"],
  };
  const [label, cls] = map[status] || [status, "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"];
  return <span className={`px-2 py-0.5 rounded text-xs ${cls}`}>{label}</span>;
}
