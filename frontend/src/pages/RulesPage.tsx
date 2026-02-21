import { useState, useEffect, useCallback } from "react";
import api from "@/api/client";
import { Plus, Edit, Trash2, GripVertical, X, HelpCircle } from "lucide-react";

interface Rule {
  id: number; name: string; enabled: boolean; rule_type: string;
  free_only: boolean; double_upload: boolean; skip_hr: boolean;
  min_size: number | null; max_size: number | null;
  min_seeders: number | null; max_seeders: number | null;
  min_leechers: number | null; max_leechers: number | null;
  keywords: string; exclude_keywords: string; categories: string;
  max_publish_hours: number | null; max_downloading: number;
  downloader_id: number | null; save_path: string; tags: string;
  account_id: number | null; sort_order: number;
}

interface Account { id: number; username: string; }
interface DL { id: number; name: string; type: string; }

const defaultForm = {
  name: "", rule_type: "normal", free_only: false, double_upload: false, skip_hr: false,
  min_size: "", max_size: "", min_seeders: "", max_seeders: "",
  min_leechers: "", max_leechers: "",
  keywords: "", exclude_keywords: "", categories: "",
  max_publish_hours: "", max_downloading: "5",
  downloader_id: "", save_path: "", tags: "",
  account_id: "", sort_order: "0", enabled: true,
};

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [downloaders, setDownloaders] = useState<DL[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(defaultForm);

  const load = useCallback(() => { api.get("/rules/").then((r) => setRules(r.data)); }, []);

  useEffect(() => {
    load();
    api.get("/accounts/").then((r) => setAccounts(r.data));
    api.get("/downloaders/").then((r) => setDownloaders(r.data));
  }, [load]);

  const openCreate = () => {
    setEditId(null);
    setForm({
      ...defaultForm,
      account_id: accounts.length > 0 ? String(accounts[0].id) : "",
      downloader_id: downloaders.length > 0 ? String(downloaders[0].id) : "",
    });
    setShowModal(true);
  };

  const openEdit = (r: Rule) => {
    setEditId(r.id);
    setForm({
      name: r.name, rule_type: r.rule_type,
      free_only: r.free_only, double_upload: r.double_upload, skip_hr: r.skip_hr,
      min_size: r.min_size?.toString() || "", max_size: r.max_size?.toString() || "",
      min_seeders: r.min_seeders?.toString() || "", max_seeders: r.max_seeders?.toString() || "",
      min_leechers: r.min_leechers?.toString() || "", max_leechers: r.max_leechers?.toString() || "",
      keywords: r.keywords, exclude_keywords: r.exclude_keywords, categories: r.categories,
      max_publish_hours: r.max_publish_hours?.toString() || "",
      max_downloading: r.max_downloading.toString(),
      downloader_id: r.downloader_id?.toString() || "",
      save_path: r.save_path, tags: r.tags,
      account_id: r.account_id?.toString() || "",
      sort_order: r.sort_order.toString(), enabled: r.enabled,
    });
    setShowModal(true);
  };

  const handleSubmit = async () => {
    const payload = {
      name: form.name, rule_type: form.rule_type,
      free_only: form.free_only, double_upload: form.double_upload, skip_hr: form.skip_hr,
      min_size: form.min_size ? +form.min_size : null, max_size: form.max_size ? +form.max_size : null,
      min_seeders: form.min_seeders ? +form.min_seeders : null, max_seeders: form.max_seeders ? +form.max_seeders : null,
      min_leechers: form.min_leechers ? +form.min_leechers : null, max_leechers: form.max_leechers ? +form.max_leechers : null,
      keywords: form.keywords, exclude_keywords: form.exclude_keywords, categories: form.categories,
      max_publish_hours: form.max_publish_hours ? +form.max_publish_hours : null,
      max_downloading: +form.max_downloading || 5,
      downloader_id: form.downloader_id ? +form.downloader_id : null,
      save_path: form.save_path, tags: form.tags,
      account_id: form.account_id ? +form.account_id : null,
      sort_order: +form.sort_order || 0,
    };
    if (editId) await api.put(`/rules/${editId}`, payload);
    else await api.post("/rules/", payload);
    setShowModal(false); load();
  };

  const handleToggle = async (id: number) => { await api.post(`/rules/${id}/toggle`); load(); };
  const handleDelete = async (id: number) => { if (!confirm("确定删除此规则？")) return; await api.delete(`/rules/${id}`); load(); };
  const set = (key: string, val: any) => setForm((f) => ({ ...f, [key]: val }));

  const conditionTags = (r: Rule) => {
    const tags: { label: string; color: string }[] = [];
    if (r.free_only) tags.push({ label: "仅免费", color: "bg-green-50 text-green-600 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-700" });
    if (r.double_upload) tags.push({ label: "2X上传", color: "bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-700" });
    if (r.skip_hr) tags.push({ label: "跳过H&R", color: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-700" });
    if (r.min_size) tags.push({ label: `≥${fmtGB(r.min_size)}`, color: "bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-700" });
    if (r.max_size) tags.push({ label: `≤${fmtGB(r.max_size)}`, color: "bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-700" });
    if (r.min_seeders != null) tags.push({ label: `做种≥${r.min_seeders}`, color: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-700" });
    if (r.max_seeders != null) tags.push({ label: `做种≤${r.max_seeders}`, color: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-700" });
    if (r.keywords) tags.push({ label: `关键词: ${r.keywords}`, color: "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-700" });
    if (r.exclude_keywords) tags.push({ label: `排除: ${r.exclude_keywords}`, color: "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600" });
    if (r.max_publish_hours) tags.push({ label: `${r.max_publish_hours}h内`, color: "bg-cyan-50 text-cyan-600 border-cyan-200 dark:bg-cyan-900/20 dark:text-cyan-400 dark:border-cyan-700" });
    return tags;
  };

  const fmtGB = (b: number) => {
    if (b >= 1024 ** 3) return (b / 1024 ** 3).toFixed(1) + "TB";
    if (b >= 1024 ** 2) return (b / 1024 ** 2).toFixed(0) + "GB";
    if (b >= 1024) return (b / 1024).toFixed(0) + "MB";
    return b + "B";
  };

  const getAccountName = (id: number | null) => accounts.find((a) => a.id === id)?.username || "-";
  const getDLName = (id: number | null) => downloaders.find((d) => d.id === id)?.name || "-";

  const Tip = ({ text }: { text: string }) => (
    <span className="inline-flex ml-1 text-gray-300 dark:text-gray-500 cursor-help" title={text}><HelpCircle size={14} /></span>
  );

  const inputCls = "w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 dark:text-white focus:bg-white dark:focus:bg-gray-600 focus:border-blue-400 focus:outline-none transition";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <span className="text-blue-500 text-lg"></span>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">自动下载规则</h1>
        </div>
        <button onClick={openCreate}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm shadow-blue-500/20">
          <Plus size={16} /> 添加规则
        </button>
      </div>

      {/* 规则列表表格 */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm overflow-hidden border border-gray-100 dark:border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-50/50 dark:bg-gray-950/50">
            <tr className="text-gray-500 dark:text-gray-400 text-xs border-b border-gray-100 dark:border-gray-800">
              <th className="text-left pl-4 pr-2 py-3 font-medium w-8"></th>
              <th className="text-left px-4 py-3 font-medium">规则名称</th>
              <th className="text-left px-4 py-3 font-medium">账号</th>
              <th className="text-left px-4 py-3 font-medium w-20">状态</th>
              <th className="text-left px-4 py-3 font-medium">条件</th>
              <th className="text-left px-4 py-3 font-medium">下载器</th>
              <th className="text-right px-5 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} className="border-b last:border-0 border-gray-100 dark:border-gray-800 hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors">
                <td className="pl-4 pr-2 py-4 text-gray-300 dark:text-gray-600 cursor-grab hover:text-gray-500"><GripVertical size={16} /></td>
                <td className="px-4 py-4"><span className="font-semibold text-gray-900 dark:text-gray-100">{r.name}</span></td>
                <td className="px-4 py-4 text-gray-500 dark:text-gray-400">{getAccountName(r.account_id)}</td>
                <td className="px-3 py-3">
                  <button onClick={() => handleToggle(r.id)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${r.enabled ? "bg-blue-500" : "bg-gray-300 dark:bg-gray-600"}`}>
                    <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${r.enabled ? "left-[1.25rem]" : "left-0.5"}`} />
                  </button>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1.5">
                    {conditionTags(r).map((t, i) => (
                      <span key={i} className={`px-2 py-1 rounded-md text-[11px] font-medium border ${t.color}`}>{t.label}</span>
                    ))}
                    {conditionTags(r).length === 0 && <span className="text-gray-400 dark:text-gray-500 text-xs italic">无条件</span>}
                  </div>
                </td>
                <td className="px-4 py-4 text-gray-500 dark:text-gray-400 text-sm font-medium">{getDLName(r.downloader_id)}</td>
                <td className="px-5 py-4">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => openEdit(r)} className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center justify-center" title="编辑">
                      <Edit size={16} />
                    </button>
                    <button onClick={() => handleDelete(r.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center justify-center" title="删除">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rules.length === 0 && (
          <div className="py-16 text-center text-gray-300 dark:text-gray-600">
            <p className="text-sm">暂无规则，点击右上角添加</p>
          </div>
        )}
      </div>

      {/* 编辑/新建模态弹窗 */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-hidden mx-4 flex flex-col border border-white/10 dark:border-gray-800"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 z-10 shrink-0">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{editId ? "编辑规则" : "添加规则"}</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"><X size={20} /></button>
            </div>

            <div className="px-6 py-5 space-y-6 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5"><span className="text-red-400">*</span> 账号</label>
                  <select value={form.account_id} onChange={(e) => set("account_id", e.target.value)} className={inputCls}>
                    <option value="">不指定</option>
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.username}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5"><span className="text-red-400">*</span> 规则名称</label>
                  <input value={form.name} onChange={(e) => set("name", e.target.value)} className={inputCls} placeholder="如：自动下载免费" />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">规则类型</label>
                  <select value={form.rule_type} onChange={(e) => set("rule_type", e.target.value)} className={inputCls}>
                    <option value="normal">普通</option>
                    <option value="favorite">收藏监控</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">排序</label>
                  <input type="number" value={form.sort_order} onChange={(e) => set("sort_order", e.target.value)} className={inputCls} />
                </div>
                <div className="flex items-end pb-1">
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">启用</label>
                  <button type="button" onClick={() => set("enabled", !form.enabled)}
                    className={`ml-3 relative w-11 h-6 rounded-full transition-colors ${form.enabled ? "bg-blue-500" : "bg-gray-300 dark:bg-gray-600"}`}>
                    <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${form.enabled ? "left-[1.375rem]" : "left-0.5"}`} />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <ToggleField label="仅免费" tip="只下载免费或2X免费种子" checked={form.free_only} onChange={(v) => set("free_only", v)} />
                <ToggleField label="2X上传" tip="只下载双倍上传种子" checked={form.double_upload} onChange={(v) => set("double_upload", v)} />
                <ToggleField label="跳过H&R" tip="跳过带有H&R标记的种子" checked={form.skip_hr} onChange={(v) => set("skip_hr", v)} />
              </div>

              <div className="grid grid-cols-4 gap-3">
                <InputField label="最小(GB)" value={form.min_size} onChange={(v) => set("min_size", v)} />
                <InputField label="最大(GB)" value={form.max_size} onChange={(v) => set("max_size", v)} />
                <InputField label="最小做种" value={form.min_seeders} onChange={(v) => set("min_seeders", v)} />
                <InputField label="最大做种" value={form.max_seeders} onChange={(v) => set("max_seeders", v)} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">关键词（逗号分隔）<Tip text="多个关键词用逗号分隔，匹配任意一个即可" /></label>
                  <input value={form.keywords} onChange={(e) => set("keywords", e.target.value)} className={inputCls} placeholder="如：4K,HDR,REMUX" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">排除关键词<Tip text="包含这些关键词的种子将被跳过" /></label>
                  <input value={form.exclude_keywords} onChange={(e) => set("exclude_keywords", e.target.value)} className={inputCls} placeholder="如：CAM,TS" />
                </div>
              </div>

              <div className="w-48">
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">发布时间限制<Tip text="只下载指定小时内发布的种子，留空不限" /></label>
                <div className="flex items-center gap-2">
                  <input type="number" value={form.max_publish_hours} onChange={(e) => set("max_publish_hours", e.target.value)} className={inputCls} placeholder="不限" />
                  <span className="text-sm text-gray-400 shrink-0">小时内</span>
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">分类筛选（分类ID，逗号分隔）</label>
                <input value={form.categories} onChange={(e) => set("categories", e.target.value)} className={inputCls} placeholder="留空不限，如：401,402" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">推送到下载器</label>
                  <select value={form.downloader_id} onChange={(e) => set("downloader_id", e.target.value)} className={inputCls}>
                    <option value="">不指定</option>
                    {downloaders.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.type})</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">最大同时下载<Tip text="该规则同时下载的种子数上限" /></label>
                  <input type="number" value={form.max_downloading} onChange={(e) => set("max_downloading", e.target.value)} className={inputCls} />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">保存路径</label>
                <input value={form.save_path} onChange={(e) => set("save_path", e.target.value)} className={inputCls} placeholder="如：/downloads/movies" />
              </div>

              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">标签<Tip text="下载器中的标签，用于分类管理" /></label>
                <input value={form.tags} onChange={(e) => set("tags", e.target.value)} className={inputCls} placeholder="如：自动下载" />
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 shrink-0">
              <button onClick={() => setShowModal(false)}
                className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 bg-white border border-gray-200 dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                取消
              </button>
              <button onClick={handleSubmit} disabled={!form.name}
                className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 shadow-sm shadow-blue-500/20 disabled:opacity-50 transition-colors">
                确定
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ToggleField({ label, tip, checked, onChange }: {
  label: string; tip: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">
        {label}
        <span className="inline-flex ml-1 text-gray-300 dark:text-gray-500 cursor-help" title={tip}><HelpCircle size={14} /></span>
      </label>
      <button type="button" onClick={() => onChange(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors ${checked ? "bg-blue-500" : "bg-gray-300 dark:bg-gray-600"}`}>
        <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${checked ? "left-[1.375rem]" : "left-0.5"}`} />
      </button>
    </div>
  );
}

function InputField({ label, value, onChange }: {
  label: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1.5">{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 dark:text-white focus:bg-white dark:focus:bg-gray-600 focus:border-blue-400 focus:outline-none transition" />
    </div>
  );
}
