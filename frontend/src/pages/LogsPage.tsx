import { useState, useEffect } from "react";
import api from "@/api/client";
import { Trash2, FileText } from "lucide-react";

interface LogFile { filename: string; size: number; modified: string; }

export default function LogsPage() {
  const [files, setFiles] = useState<LogFile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);

  const load = () => api.get("/logs/").then((r) => setFiles(r.data));
  useEffect(() => { load(); }, []);

  const viewLog = async (filename: string) => {
    setSelected(filename);
    const r = await api.get(`/logs/${filename}`);
    setLines(r.data.lines);
  };

  const deleteLog = async (filename: string) => {
    if (!confirm(`确定删除 ${filename}？`)) return;
    await api.delete(`/logs/${filename}`);
    if (selected === filename) { setSelected(null); setLines([]); }
    load();
  };

  const fmtSize = (b: number) => b > 1024 * 1024 ? (b / 1024 / 1024).toFixed(1) + " MB" : (b / 1024).toFixed(1) + " KB";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">日志管理</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800 font-semibold text-gray-900 dark:text-white bg-gray-50/50 dark:bg-gray-950/50 shrink-0">日志文件</div>
          {files.length === 0 ? (
            <div className="p-4 text-gray-400 text-sm">暂无日志文件</div>
          ) : (
            <div className="divide-y border-gray-100 dark:divide-gray-800 overflow-y-auto max-h-[600px]">
              {files.map((f) => (
                <div key={f.filename}
                  className={`flex items-center justify-between px-5 py-4 cursor-pointer transition-colors ${selected === f.filename
                      ? "bg-blue-50/50 dark:bg-blue-900/10 border-l-2 border-l-blue-500"
                      : "hover:bg-gray-50 dark:hover:bg-gray-800/50 border-l-2 border-l-transparent"
                    }`}
                  onClick={() => viewLog(f.filename)}>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl ${selected === f.filename ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}`}>
                      <FileText size={16} />
                    </div>
                    <div>
                      <div className={`text-sm font-medium ${selected === f.filename ? 'text-blue-700 dark:text-blue-400' : 'text-gray-700 dark:text-gray-200'}`}>{f.filename}</div>
                      <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{fmtSize(f.size)}</div>
                    </div>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); deleteLog(f.filename); }} title="删除文件"
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 items-end">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden flex flex-col h-[660px]">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800 font-semibold text-gray-900 dark:text-white bg-gray-50/50 dark:bg-gray-950/50 shrink-0">
            {selected || "选择日志文件查看"}
          </div>
          <div className="p-5 flex-1 overflow-auto bg-gray-50/30 dark:bg-[#0d1117] relative">
            {lines.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">暂无内容</div>
            ) : (
              <pre className="text-xs text-gray-800 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                {lines.join("")}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
