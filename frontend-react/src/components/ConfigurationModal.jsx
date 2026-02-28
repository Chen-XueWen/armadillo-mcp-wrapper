import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, RotateCcw, Settings } from 'lucide-react';

const ConfigurationModal = ({ isOpen, onClose, config, onSave }) => {
    const [localConfig, setLocalConfig] = useState(config);

    // Reset local state when modal opens with new config
    useEffect(() => {
        if (isOpen) {
            setLocalConfig(config);
        }
    }, [isOpen, config]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setLocalConfig(prev => ({
            ...prev,
            [name]: parseFloat(value) || 0
        }));
    };

    const handleReset = () => {
        setLocalConfig({
            blockedMultiplier: 5,
            pendingMultiplier: 2,
            scaleFactor: 10
        });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(localConfig);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                />
                <motion.div
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: 20 }}
                    className="relative bg-slate-900 border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl overflow-hidden"
                >
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-50" />

                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                                <Settings className="w-5 h-5" />
                            </div>
                            <h2 className="text-xl font-bold text-white">Risk Configuration</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                                    Blocked Request Multiplier
                                </label>
                                <input
                                    type="number"
                                    name="blockedMultiplier"
                                    value={localConfig.blockedMultiplier}
                                    onChange={handleChange}
                                    step="0.1"
                                    className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all font-mono"
                                />
                                <p className="text-xs text-slate-500 mt-1.5">Weight assigned to blocked threats.</p>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                                    Pending Action Multiplier
                                </label>
                                <input
                                    type="number"
                                    name="pendingMultiplier"
                                    value={localConfig.pendingMultiplier}
                                    onChange={handleChange}
                                    step="0.1"
                                    className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all font-mono"
                                />
                                <p className="text-xs text-slate-500 mt-1.5">Weight assigned to pending approvals.</p>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                                    Global Scale Factor
                                </label>
                                <input
                                    type="number"
                                    name="scaleFactor"
                                    value={localConfig.scaleFactor}
                                    onChange={handleChange}
                                    step="1"
                                    className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all font-mono"
                                />
                                <p className="text-xs text-slate-500 mt-1.5">Base scaling factor for the final score.</p>
                            </div>
                        </div>

                        <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                            <div className="text-xs text-slate-400 font-mono mb-2 opacity-70">CURRENT FORMULA</div>
                            <div className="font-mono text-xs text-indigo-300">
                                ((blocked * {localConfig.blockedMultiplier} + pending * {localConfig.pendingMultiplier}) / total * {localConfig.scaleFactor})
                            </div>
                        </div>

                        <div className="flex items-center gap-3 pt-2">
                            <button
                                type="button"
                                onClick={handleReset}
                                className="px-4 py-2.5 rounded-xl bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 border border-white/5 transition-all text-sm font-medium flex items-center gap-2"
                            >
                                <RotateCcw className="w-4 h-4" />
                                <span className="hidden sm:inline">Reset Defaults</span>
                            </button>
                            <button
                                type="submit"
                                className="flex-1 px-4 py-2.5 rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 border border-indigo-500 shadow-lg shadow-indigo-500/20 transition-all text-sm font-bold flex items-center justify-center gap-2"
                            >
                                <Save className="w-4 h-4" />
                                Save Changes
                            </button>
                        </div>
                    </form>
                </motion.div>
            </div>
        </AnimatePresence>
    );
};

export default ConfigurationModal;
