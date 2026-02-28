import { useState } from 'react';
import { Search, ArrowRight, Database, Shield } from 'lucide-react';
import { motion as Motion } from 'framer-motion';

const AuditLog = ({ requests }) => {
    const [searchTerm, setSearchTerm] = useState('');

    const filteredData = requests.filter(row =>
        row.tool_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        row.status.toLowerCase().includes(searchTerm.toLowerCase()) ||
        row.args.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const getStatusBadge = (status) => {
        const styles = {
            APPROVED: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 shadow-[0_0_10px_rgba(99,102,241,0.2)]",
            DENIED: "bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_10px_rgba(248,113,113,0.2)]",
            BLOCKED: "bg-red-500/10 text-red-400 border-red-500/20",
            COMPLETED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]",
            PENDING: "bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.2)]",
        };
        const defaultStyle = "bg-slate-500/10 text-slate-400 border-slate-500/20";

        return (
            <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${styles[status] || defaultStyle} uppercase tracking-widest flex w-fit items-center gap-1.5`}>
                <span className={`w-1.5 h-1.5 rounded-full ${status === 'PENDING' ? 'animate-pulse bg-current' : 'bg-current'}`} />
                {status}
            </span>
        );
    };

    return (
        <Motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-12rem)]"
        >
            <div className="p-6 border-b border-white/5 flex items-center justify-between gap-6 bg-white/5 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                        <Database className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="font-bold text-lg text-white tracking-tight">System Activity Log</h2>
                        <p className="text-sm text-slate-400">Immutable record of all tool executions</p>
                    </div>
                </div>
                <div className="relative group">
                    <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
                    <input
                        type="text"
                        placeholder="Search logs..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10 pr-4 py-2.5 bg-slate-900/50 border border-white/10 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all w-80 text-slate-200 placeholder:text-slate-600 shadow-inner"
                    />
                </div>
            </div>

            <div className="overflow-auto flex-1 custom-scrollbar">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-950/50 text-slate-400 sticky top-0 z-10 backdrop-blur-sm">
                        <tr>
                            <th className="px-8 py-4 text-[10px] font-bold uppercase tracking-widest border-b border-white/5">Time</th>
                            <th className="px-8 py-4 text-[10px] font-bold uppercase tracking-widest border-b border-white/5">Agent</th>
                            <th className="px-8 py-4 text-[10px] font-bold uppercase tracking-widest border-b border-white/5">Status</th>
                            <th className="px-8 py-4 text-[10px] font-bold uppercase tracking-widest border-b border-white/5">Tool Usage</th>
                            <th className="px-8 py-4 text-[10px] font-bold uppercase tracking-widest border-b border-white/5">Parameters</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {filteredData.map((row) => (
                            <tr key={row.id} className="group hover:bg-white/5 transition-colors">
                                <td className="px-8 py-4">
                                    <div className="flex flex-col">
                                        <span className="font-mono text-xs text-white font-medium">
                                            {new Date(row.timestamp).toLocaleTimeString()}
                                        </span>
                                        <span className="text-[10px] text-slate-500 mt-0.5">
                                            {new Date(row.timestamp).toLocaleDateString()}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-8 py-4">
                                    <span className="bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20 text-indigo-300 font-mono text-[10px] font-bold">
                                        {row.agent_id || 'Unknown'}
                                    </span>
                                </td>
                                <td className="px-8 py-4">{getStatusBadge(row.status)}</td>
                                <td className="px-8 py-4">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-slate-200 text-sm">{row.tool_name}</span>
                                        {String(row.risk_level || '').toLowerCase() === 'high' && (
                                            <Shield className="w-3 h-3 text-red-400" />
                                        )}
                                    </div>
                                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">{row.risk_level} risk</span>
                                </td>
                                <td className="px-8 py-4 max-w-lg">
                                    <div className="font-mono text-[10px] text-indigo-300/80 truncate bg-slate-950/50 border border-white/5 rounded px-2 py-1.5 group-hover:text-indigo-300 transition-colors">
                                        {row.args}
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {filteredData.length === 0 && (
                            <tr>
                                <td colSpan="5" className="text-center py-20 text-slate-500">
                                    No records found matching your search.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <div className="p-4 border-t border-white/5 bg-slate-900/30 flex justify-center backdrop-blur-sm">
                <button className="text-xs font-bold text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-2 uppercase tracking-widest group">
                    View Entire History <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                </button>
            </div>
        </Motion.div >
    );
};

export default AuditLog;
