import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Activity, ShieldAlert, Clock, AlertTriangle, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

const StatCard = ({ title, value, icon: Icon, trend, color, delay }) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="glass-panel p-6 rounded-2xl relative group hover:border-white/10 transition-colors"
    >
        <div className="absolute inset-0 overflow-hidden rounded-2xl pointer-events-none">
            <div className={`absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-10 transition-opacity transform group-hover:scale-110 duration-500 delay-75`}>
                <Icon className={`w-32 h-32 ${color.text}`} />
            </div>
        </div>

        <div className="relative z-10">
            <div className="flex items-center justify-between mb-4 gap-4">
                <div className={`p-3 rounded-xl bg-white/5 border border-white/5 ${color.text}`}>
                    <Icon className="w-6 h-6" />
                </div>
                {trend && (
                    <div className={`flex items-center gap-1 text-xs font-bold px-3 py-1.5 rounded-full border ${trend === 'high' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}>
                        {trend === 'high' ? <TrendingUp className="w-3 h-3" /> : <Activity className="w-3 h-3" />}
                        <span>{trend === 'high' ? 'CRITICAL' : 'NOMINAL'}</span>
                    </div>
                )}
            </div>
            <div>
                <h3 className="text-slate-400 text-xs font-bold tracking-widest uppercase mb-1">{title}</h3>
                <div className="flex items-baseline gap-2">
                    <h2 className="text-3xl font-bold text-white tracking-tight">{value}</h2>
                </div>
            </div>
        </div>
    </motion.div>
);

const Dashboard = ({ data, stats, riskConfig = { blockedMultiplier: 5, pendingMultiplier: 2, scaleFactor: 10 } }) => {
    // Use stats from backend if available for global counters, otherwise fallback to local data length (for initial load/compat)
    const total = stats?.total_requests ?? data.length;
    const pending = stats?.total_pending ?? data.filter(r => r.status === 'PENDING').length;
    const blocked = stats?.total_blocked ?? data.filter(r => r.status === 'BLOCKED').length;

    // Risk score calculation
    const riskScore = total > 0
        ? ((blocked * riskConfig.blockedMultiplier + pending * riskConfig.pendingMultiplier) / total * riskConfig.scaleFactor).toFixed(1)
        : 0;

    // Process chart data
    const timeData = data.slice().reverse().map(r => ({
        time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        count: 1
    }));

    const chartData = timeData.reduce((acc, curr) => {
        const last = acc[acc.length - 1];
        if (last && last.time === curr.time) {
            last.count += 1;
        } else {
            acc.push({ ...curr });
        }
        return acc;
    }, []);

    const toolData = Object.entries(data.reduce((acc, curr) => {
        acc[curr.tool_name] = (acc[curr.tool_name] || 0) + 1;
        return acc;
    }, {})).map(([name, value]) => ({ name, value }));

    const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b'];

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Requests"
                    value={total}
                    icon={Activity}
                    color={{ text: 'text-indigo-400' }}
                    delay={0}
                />
                <StatCard
                    title="Pending Actions"
                    value={pending}
                    icon={Clock}
                    color={{ text: 'text-amber-400' }}
                    trend={pending > 0 ? 'high' : 'low'}
                    delay={0.1}
                />
                <StatCard
                    title="Blocked Threats"
                    value={blocked}
                    icon={ShieldAlert}
                    color={{ text: 'text-red-400' }}
                    delay={0.2}
                />
                <StatCard
                    title="Risk Score"
                    value={riskScore}
                    icon={AlertTriangle}
                    color={{ text: 'text-slate-400' }}
                    trend={riskScore > 5 ? 'high' : 'low'}
                    delay={0.3}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.4 }}
                    className="lg:col-span-2 glass-panel p-8 rounded-2xl"
                >
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h3 className="text-lg font-bold text-white">Traffic Velocity</h3>
                            <p className="text-sm text-slate-400">Real-time request throughput</p>
                        </div>
                    </div>
                    <div className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.5} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={10} />
                                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-10} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.5)', color: '#fff' }}
                                    itemStyle={{ color: '#fff' }}
                                    cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }}
                                />
                                <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorCount)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                    className="glass-panel p-8 rounded-2xl"
                >
                    <div className="mb-8">
                        <h3 className="text-lg font-bold text-white">Tool Distribution</h3>
                        <p className="text-sm text-slate-400">Usage by tool type</p>
                    </div>
                    <div className="h-[350px] relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={toolData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={80}
                                    outerRadius={100}
                                    paddingAngle={5}
                                    dataKey="value"
                                    cornerRadius={6}
                                    stroke="none"
                                >
                                    {toolData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div className="text-center">
                                <p className="text-4xl font-bold text-white">{total}</p>
                                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mt-1">Requests</p>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default Dashboard;
