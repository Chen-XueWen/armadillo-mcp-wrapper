import React from 'react';
import { Copy, Check, X, ShieldAlert, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

const ActionCenter = ({ data, refreshData }) => {
    const pendingRequests = data.filter(r => r.status === 'PENDING');

    const handleAction = async (id, action) => {
        try {
            await axios.post(`http://localhost:8000/api/${action}/${id}`);
            refreshData();
        } catch (error) {
            console.error(`Failed to ${action} request`, error);
        }
    };

    if (pendingRequests.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center min-h-[500px] text-center"
            >
                <div className="w-32 h-32 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 shadow-[0_0_40px_rgba(16,185,129,0.2)] border border-emerald-500/20">
                    <Check className="w-16 h-16 text-emerald-500" />
                </div>
                <h3 className="text-3xl font-bold text-white tracking-tight">All Systems Nominal</h3>
                <p className="text-slate-400 mt-3 max-w-sm text-lg">There are no pending actions requiring human intervention at this time.</p>
            </motion.div>
        );
    }

    return (
        <div className="space-y-6 w-full">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-3xl font-bold text-white tracking-tight">Pending Approvals</h2>
                    <p className="text-slate-400 mt-2">Review potentially risky tool executions. Requests will automatically timeout in 60 seconds.</p>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 px-6 py-2 rounded-full text-sm font-bold shadow-[0_0_20px_rgba(245,158,11,0.2)] flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                    </span>
                    {pendingRequests.length} ACTION REQUIRED
                </div>
            </div>

            <AnimatePresence>
                {pendingRequests.map((req) => (
                    <motion.div
                        key={req.id}
                        layout
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -100 }}
                        className="glass-panel rounded-2xl overflow-hidden group border border-white/5 hover:border-indigo-500/50 transition-all duration-300 relative"
                    >
                        <div className="absolute top-0 left-0 w-1 h-full bg-amber-500" />

                        <div className="grid grid-cols-12 gap-0">
                            {/* Status Strip */}
                            <div className="col-span-1 bg-amber-500/5 border-r border-white/5 flex items-center justify-center flex-col gap-2 py-4">
                                <ShieldAlert className="w-8 h-8 text-amber-500 animate-pulse" />
                            </div>

                            {/* Content */}
                            <div className="col-span-11 p-8">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <div className="flex items-center gap-4 mb-2">
                                            <h3 className="text-2xl font-bold text-white tracking-tight">{req.tool_name}</h3>
                                            <span className="text-xs font-mono text-slate-400 bg-white/5 px-2 py-1 rounded border border-white/10">{req.id.slice(0, 8)}</span>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2 text-amber-400 font-medium">
                                                <AlertTriangle className="w-4 h-4" />
                                                <span>Policy Flag: {req.policy_reason}</span>
                                            </div>
                                            <div className="flex items-center gap-2 text-indigo-300 font-mono text-xs mt-1">
                                                <span className="opacity-70">Requested by:</span>
                                                <span className="bg-indigo-500/20 px-2 py-0.5 rounded border border-indigo-500/30 text-indigo-300 font-bold">
                                                    {req.agent_id || 'Unknown'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <span className="text-xs font-bold tracking-widest text-amber-400 uppercase bg-amber-500/10 px-4 py-2 rounded-lg border border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.15)] h-fit">
                                        {req.risk_level} Risk
                                    </span>
                                </div>

                                <div className="bg-black/30 rounded-xl p-5 mb-8 relative group/code border border-white/5 overflow-hidden">
                                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-20" />
                                    <pre className="text-sm font-mono text-indigo-300 overflow-x-auto">
                                        {JSON.stringify(JSON.parse(req.args.replaceAll("'", '"')), null, 2)}
                                    </pre>
                                    <div className="absolute top-2 right-2 p-2 opacity-50 group-hover/code:opacity-100 transition-opacity">
                                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">JSON Payload</span>
                                    </div>
                                </div>

                                <div className="flex gap-4 justify-end">
                                    <button
                                        onClick={() => handleAction(req.id, 'deny')}
                                        className="px-8 py-3 text-slate-300 bg-white/5 border border-white/10 font-semibold rounded-xl hover:bg-white/10 hover:text-white hover:border-white/20 transition-all text-sm uppercase tracking-wide"
                                    >
                                        Deny Request
                                    </button>
                                    <button
                                        onClick={() => handleAction(req.id, 'approve')}
                                        className="px-8 py-3 text-white bg-indigo-600 font-semibold rounded-xl hover:bg-indigo-500 hover:shadow-[0_0_25px_rgba(79,70,229,0.4)] transition-all shadow-lg shadow-indigo-500/20 text-sm flex items-center gap-2 border border-indigo-500 uppercase tracking-wide"
                                    >
                                        <Check className="w-5 h-5" />
                                        Approve Execution
                                    </button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
};

export default ActionCenter;
