import { useState, useEffect } from "react";
import api from "@/api/client";
import { Save, RotateCw } from "lucide-react";

export default function SettingsPage() {
  const [autoDelete, setAutoDelete] = useState<any>(null);
  const [intervals, setIntervals] = useState<any>(null);
  const [schedule, setSchedule] = useState<any>(null);
  const [scheduler, setScheduler] = useState<any>(null);
  const [saving, setSaving] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.get("/settings/auto-delete").then((r) => setAutoDelete(r.data));
    api.get("/settings/refresh-intervals").then((r) => setIntervals(r.data));
    api.get("/settings/schedule-control").then((r) => setSchedule(r.data));
    api.get("/settings/scheduler-status").then((r) => setScheduler(r.data));
  }, []);

  const save = async (key: string, value: any) => {
    setSaving(key); setMsg("");
    try { await api.put(`/settings/${key}`, { value }); setMsg(`${key} 已保存`); }
    finally { setSaving(""); }
  };

  const restartScheduler = async () => {
    setSaving("restart");
    const r = await api.post("/settings/restart-scheduler");
    setScheduler(r.data.status); setMsg("调度器已重启"); setSaving("");
  };

  if (!autoDelete || !intervals || !schedule) return <div className="text-gray-500 dark:text-gray-400">加载中...</div>;

  const Toggle = ({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) => (
    <label className="flex items-center justify-between py-2">
      <span className="text-sm dark:text-gray-300">{label}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="w-4 h-4 accent-blue-600" />
    </label>
  );

  const NumField = ({ label, value, onChange, suffix = "分钟" }: any) => (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm dark:text-gray-300">{label}</span>
      <div className="flex items-center gap-1">
        <input type="number" value={value} onChange={(e) => onChange(+e.target.value)}
          className="w-20 border dark:border-gray-600 rounded px-2 py-1 text-sm text-right dark:bg-gray-700 dark:text-white" />
        <span className="text-xs text-gray-400">{suffix}</span>
      </div>
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">系统设置</h1>
        {msg && <span className="text-sm font-medium text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400 px-3 py-1.5 rounded-lg">{msg}</span>}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 调度控制 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-6 border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">定时任务开关</h2>
            <div className="flex gap-2">
              <button onClick={restartScheduler} disabled={saving === "restart"}
                className="flex items-center gap-1.5 text-sm font-medium bg-gray-50 text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors">
                <RotateCw size={14} className={saving === "restart" ? "animate-spin" : ""} /> 重启调度
              </button>
              <button onClick={() => save("schedule-control", schedule)} disabled={saving === "schedule-control"}
                className="flex items-center gap-1.5 text-sm font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/40 px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
                <Save size={14} /> 保存
              </button>
            </div>
          </div>
          <div className="divide-y dark:divide-gray-700">
            <Toggle label="自动下载" checked={schedule.auto_download_enabled} onChange={(v) => setSchedule({ ...schedule, auto_download_enabled: v })} />
            <Toggle label="账号刷新" checked={schedule.account_refresh_enabled} onChange={(v) => setSchedule({ ...schedule, account_refresh_enabled: v })} />
            <Toggle label="状态同步" checked={schedule.status_sync_enabled} onChange={(v) => setSchedule({ ...schedule, status_sync_enabled: v })} />
            <Toggle label="过期检查" checked={schedule.expired_check_enabled} onChange={(v) => setSchedule({ ...schedule, expired_check_enabled: v })} />
            <Toggle label="动态删种" checked={schedule.dynamic_delete_enabled} onChange={(v) => setSchedule({ ...schedule, dynamic_delete_enabled: v })} />
            <Toggle label="失效种子检查" checked={schedule.unregistered_check_enabled} onChange={(v) => setSchedule({ ...schedule, unregistered_check_enabled: v })} />
          </div>
          {scheduler && (
            <div className="mt-3 text-xs text-gray-400">
              调度器状态: {scheduler.running ? "运行中" : "已停止"} | 任务数: {scheduler.jobs?.length || 0}
            </div>
          )}
        </div>

        {/* 刷新间隔 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-6 border border-gray-100 dark:border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">刷新间隔</h2>
            <button onClick={() => save("refresh-intervals", intervals)} disabled={saving === "refresh-intervals"}
              className="flex items-center gap-1.5 text-sm font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/40 px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
              <Save size={14} /> 保存
            </button>
          </div>
          <div className="divide-y dark:divide-gray-700">
            <NumField label="自动下载" value={intervals.auto_download_minutes} onChange={(v: number) => setIntervals({ ...intervals, auto_download_minutes: v })} />
            <NumField label="账号刷新" value={intervals.account_refresh_minutes} onChange={(v: number) => setIntervals({ ...intervals, account_refresh_minutes: v })} />
            <NumField label="状态同步" value={intervals.status_sync_minutes} onChange={(v: number) => setIntervals({ ...intervals, status_sync_minutes: v })} />
            <NumField label="过期检查" value={intervals.expired_check_minutes} onChange={(v: number) => setIntervals({ ...intervals, expired_check_minutes: v })} />
            <NumField label="动态删种" value={intervals.dynamic_delete_minutes} onChange={(v: number) => setIntervals({ ...intervals, dynamic_delete_minutes: v })} />
            <NumField label="失效种子检查" value={intervals.unregistered_check_minutes} onChange={(v: number) => setIntervals({ ...intervals, unregistered_check_minutes: v })} />
          </div>
        </div>

        {/* 自动删种 */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm p-6 border border-gray-100 dark:border-gray-800 xl:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">自动删种设置</h2>
              <p className="text-xs text-gray-400 mt-0.5">所有删种规则仅在「启用自动删种」开启时生效，H&R 考核中的种子永远不会被自动删除</p>
            </div>
            <button onClick={() => save("auto-delete", autoDelete)} disabled={saving === "auto-delete"}
              className="flex items-center gap-1.5 text-sm font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/40 px-3 py-1.5 rounded-lg disabled:opacity-50 transition-colors">
              <Save size={14} /> 保存
            </button>
          </div>

          <div className="space-y-5">
            {/* 总开关 */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700">
              <div>
                <span className="text-sm font-medium dark:text-gray-200">启用自动删种</span>
                <p className="text-xs text-gray-400 mt-0.5">主开关，关闭后以下所有规则均不执行</p>
              </div>
              <input type="checkbox" checked={autoDelete.enabled} onChange={(e) => setAutoDelete({ ...autoDelete, enabled: e.target.checked })} className="w-4 h-4 accent-blue-600" />
            </div>

            {/* 促销过期 */}
            <div className={`space-y-0 rounded-xl border ${autoDelete.enabled ? "border-gray-100 dark:border-gray-700" : "border-gray-100/50 dark:border-gray-700/50 opacity-50 pointer-events-none"}`}>
              <div className="px-4 py-2 bg-gray-50/80 dark:bg-gray-800/30 rounded-t-xl border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">促销过期</span>
              </div>
              <div className="px-4 divide-y dark:divide-gray-700/50">
                <label className="flex items-center justify-between py-3">
                  <div>
                    <span className="text-sm dark:text-gray-300">删除促销到期的种子</span>
                    <p className="text-xs text-gray-400 mt-0.5">免费、2x 等促销结束后自动处理该种子</p>
                  </div>
                  <input type="checkbox" checked={autoDelete.delete_expired} onChange={(e) => setAutoDelete({ ...autoDelete, delete_expired: e.target.checked })} className="w-4 h-4 accent-blue-600 ml-4 shrink-0" />
                </label>
                <div className="flex items-center justify-between py-3">
                  <div>
                    <span className="text-sm dark:text-gray-300">促销到期执行动作</span>
                    <p className="text-xs text-gray-400 mt-0.5">H&R 考核中的种子无论此设置如何，始终只暂停不删除</p>
                  </div>
                  <select value={autoDelete.expired_action || "delete"}
                    onChange={(e) => setAutoDelete({ ...autoDelete, expired_action: e.target.value })}
                    className="border dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm dark:bg-gray-700 dark:text-white ml-4 shrink-0">
                    <option value="delete">删除种子 + 本地文件</option>
                    <option value="pause">仅暂停，保留文件</option>
                  </select>
                </div>
                <label className="flex items-center justify-between py-3">
                  <div>
                    <span className="text-sm dark:text-gray-300">删除下载中的非免费种子</span>
                    <p className="text-xs text-gray-400 mt-0.5">仅针对还在下载中的种子，若当前不是免费促销则直接删除</p>
                  </div>
                  <input type="checkbox" checked={autoDelete.delete_non_free} onChange={(e) => setAutoDelete({ ...autoDelete, delete_non_free: e.target.checked })} className="w-4 h-4 accent-blue-600 ml-4 shrink-0" />
                </label>
              </div>
            </div>

            {/* 容量管理 */}
            <div className={`space-y-0 rounded-xl border ${autoDelete.enabled ? "border-gray-100 dark:border-gray-700" : "border-gray-100/50 dark:border-gray-700/50 opacity-50 pointer-events-none"}`}>
              <div className="px-4 py-2 bg-gray-50/80 dark:bg-gray-800/30 rounded-t-xl border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">容量管理</span>
              </div>
              <div className="px-4 divide-y dark:divide-gray-700/50">
                <label className="flex items-center justify-between py-3">
                  <div>
                    <span className="text-sm dark:text-gray-300">启用动态容量删种</span>
                    <p className="text-xs text-gray-400 mt-0.5">已用空间超过上限时，按做种时间从旧到新自动删除，直到降至目标用量</p>
                  </div>
                  <input type="checkbox" checked={autoDelete.dynamic_delete_enabled} onChange={(e) => setAutoDelete({ ...autoDelete, dynamic_delete_enabled: e.target.checked })} className="w-4 h-4 accent-blue-600 ml-4 shrink-0" />
                </label>
                {autoDelete.dynamic_delete_enabled && (
                  <div className="py-3 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm dark:text-gray-300">触发上限</span>
                        <p className="text-xs text-gray-400 mt-0.5">已用空间 ≥ 此值时开始删种</p>
                      </div>
                      <div className="flex items-center gap-1.5 ml-4 shrink-0">
                        <input type="number" value={autoDelete.disk_max_gb ?? 10000}
                          onChange={(e) => setAutoDelete({ ...autoDelete, disk_max_gb: +e.target.value })}
                          className="w-24 border dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm text-right dark:bg-gray-700 dark:text-white" />
                        <span className="text-xs text-gray-400">GB</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm dark:text-gray-300">目标用量</span>
                        <p className="text-xs text-gray-400 mt-0.5">删种后已用空间降至此值时停止</p>
                      </div>
                      <div className="flex items-center gap-1.5 ml-4 shrink-0">
                        <input type="number" value={autoDelete.disk_target_gb ?? 8000}
                          onChange={(e) => setAutoDelete({ ...autoDelete, disk_target_gb: +e.target.value })}
                          className="w-24 border dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm text-right dark:bg-gray-700 dark:text-white" />
                        <span className="text-xs text-gray-400">GB</span>
                      </div>
                    </div>
                    {(autoDelete.disk_target_gb ?? 8000) >= (autoDelete.disk_max_gb ?? 10000) && (
                      <p className="text-xs text-red-500">目标用量必须小于触发上限</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* 失效种子 */}
            <div className={`space-y-0 rounded-xl border ${autoDelete.enabled ? "border-gray-100 dark:border-gray-700" : "border-gray-100/50 dark:border-gray-700/50 opacity-50 pointer-events-none"}`}>
              <div className="px-4 py-2 bg-gray-50/80 dark:bg-gray-800/30 rounded-t-xl border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">失效种子</span>
              </div>
              <div className="px-4">
                <label className="flex items-center justify-between py-3">
                  <div>
                    <span className="text-sm dark:text-gray-300">删除站点已下架的种子</span>
                    <p className="text-xs text-gray-400 mt-0.5">Tracker 返回 Unregistered 状态，说明该种子已从站点移除</p>
                  </div>
                  <input type="checkbox" checked={autoDelete.delete_unregistered} onChange={(e) => setAutoDelete({ ...autoDelete, delete_unregistered: e.target.checked })} className="w-4 h-4 accent-blue-600 ml-4 shrink-0" />
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
