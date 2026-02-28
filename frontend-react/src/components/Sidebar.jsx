import { LayoutDashboard, Zap, FileText, Shield, ChevronRight, Network } from 'lucide-react';
import { motion as Motion } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const Sidebar = ({ activeTab, setActiveTab }) => {
    const menuItems = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'actions', label: 'Action Center', icon: Zap },
        { id: 'audit', label: 'Audit Log', icon: FileText },
        { id: 'platform', label: 'Access Management', icon: Network },
    ];

    return (
        <div className="w-72 h-full flex flex-col border-r border-white/5 bg-slate-950/30 backdrop-blur-xl relative z-20">
            <div className="p-8">
                <div className="p-6 border-b border-white/5 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.3)]">
                        <Shield className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <h1 className="font-bold text-lg text-white whitespace-nowrap">GOVERNOR-MCP</h1>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-400 font-semibold">CONTROL PANEL</p>
                    </div>
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-2">
                <div className="px-4 pb-2">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Platform</p>
                </div>
                {menuItems.map((item) => {
                    const isActive = activeTab === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={twMerge(
                                clsx(
                                    "relative group w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium transition-all duration-300",
                                    isActive
                                        ? "text-white bg-white/5 border border-white/10 shadow-[0_0_20px_rgba(0,0,0,0.2)]"
                                        : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"
                                )
                            )}
                        >
                            {isActive && (
                                <Motion.div
                                    layoutId="activeTabIndicator"
                                    className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-transparent rounded-xl pointer-events-none"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                />
                            )}
                            {isActive && (
                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-indigo-500 rounded-r-full shadow-[0_0_10px_#6366f1]" />
                            )}

                            <item.icon className={clsx("w-5 h-5 transition-colors relative z-10", isActive ? "text-indigo-400 drop-shadow-[0_0_8px_rgba(129,140,248,0.5)]" : "text-slate-500 group-hover:text-slate-300")} />
                            <span className="flex-1 text-left relative z-10">{item.label}</span>
                            {isActive && <ChevronRight className="w-4 h-4 text-indigo-400/50" />}
                        </button>
                    );
                })}
            </nav>

            <div className="p-4">
                <div className="rounded-xl p-4 border border-white/5 bg-white/5 backdrop-blur-sm relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                    <div className="relative z-10">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                            <span className="text-xs font-medium text-emerald-400">System Operational</span>
                        </div>
                        <p className="text-[10px] text-slate-500 leading-relaxed font-mono">
                            Connected to <strong className="text-slate-300">Localhost</strong><br />
                            Latency: <strong className="text-emerald-400">2ms</strong>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
