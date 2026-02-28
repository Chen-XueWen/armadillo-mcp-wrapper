import { useMemo, useState } from 'react';
import { motion as Motion } from 'framer-motion';
import { UserRound, ShieldCheck, Lock, ShieldAlert, CircleCheck, Plus, Unlink, Trash2 } from 'lucide-react';
import { api } from '../api';

const effectClasses = {
    ALLOW: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    REVIEW: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    DENY: "bg-red-500/10 text-red-300 border-red-500/30",
};
const API_BASE = "/api/access-control";
const EMPTY_LIST = [];

const getErrorMessage = (error) => {
    return error?.response?.data?.detail || error?.message || "Failed to update access control";
};

const normalizeResource = (resource) => {
    if (!resource) return '*';
    return resource.startsWith('tool:') ? resource.replace('tool:', '') : resource;
};

const EffectBadge = ({ effect }) => (
    <span className={`text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full border ${effectClasses[effect] || "bg-slate-500/10 text-slate-300 border-slate-500/30"}`}>
        {effect}
    </span>
);

const AgentCard = ({ agent, index, allPolicies, busy, onAttachPolicy, onDetachPolicy, onDeleteStatement, onRemoveAgent }) => {
    const statements = agent.statements || [];
    const allows = statements.filter(s => s.effect === 'ALLOW').length;
    const reviews = statements.filter(s => s.effect === 'REVIEW').length;
    const denies = statements.filter(s => s.effect === 'DENY').length;
    const isWildcardAgent = agent.id === "*";
    const attachablePolicies = allPolicies.filter((policy) => !(agent.attached_policies || []).includes(policy.id));
    const [selectedPolicyId, setSelectedPolicyId] = useState(attachablePolicies[0]?.id || "");
    const effectivePolicyId = attachablePolicies.some((policy) => policy.id === selectedPolicyId)
        ? selectedPolicyId
        : (attachablePolicies[0]?.id || "");

    return (
        <Motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06 }}
            className="glass-panel rounded-2xl p-6 border border-white/5"
        >
            <div className="flex items-start justify-between gap-6 mb-4">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <UserRound className="w-4 h-4 text-indigo-300" />
                        <h3 className="text-lg font-bold text-white">{agent.name || agent.id}</h3>
                    </div>
                    <p className="text-xs font-mono text-slate-400">{agent.id}</p>
                </div>
                <div className="flex gap-2">
                    <span className="text-[10px] uppercase tracking-widest text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-full">{allows} allow</span>
                    <span className="text-[10px] uppercase tracking-widest text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded-full">{reviews} review</span>
                    <span className="text-[10px] uppercase tracking-widest text-red-300 bg-red-500/10 border border-red-500/20 px-2 py-1 rounded-full">{denies} deny</span>
                    <button
                        onClick={() => onRemoveAgent(agent.id)}
                        className="px-2 py-1 rounded-full border border-red-500/20 bg-red-500/10 text-red-300 hover:bg-red-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={busy || isWildcardAgent}
                        title={isWildcardAgent ? "Wildcard baseline agent cannot be removed" : "Remove agent"}
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            <div className="mb-5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Attached Policies</p>
                <div className="flex flex-wrap gap-2">
                    {(agent.attached_policies || []).map((policyId) => (
                        <div key={policyId} className="text-xs text-indigo-200 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-lg font-mono flex items-center gap-2">
                            <span>{policyId}</span>
                            <button
                                onClick={() => onDetachPolicy(agent.id, policyId)}
                                className="text-slate-300 hover:text-red-300 transition-colors disabled:opacity-50"
                                disabled={busy}
                                title="Detach policy"
                            >
                                <Unlink className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                    {(!agent.attached_policies || agent.attached_policies.length === 0) && (
                        <span className="text-xs text-slate-400">No policies attached</span>
                    )}
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                    <select
                        value={effectivePolicyId}
                        onChange={(event) => setSelectedPolicyId(event.target.value)}
                        className="bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-xs text-slate-200 min-w-[230px]"
                        disabled={busy || attachablePolicies.length === 0}
                    >
                        {attachablePolicies.length === 0 && <option value="">No remaining policies</option>}
                        {attachablePolicies.map((policy) => (
                            <option key={policy.id} value={policy.id}>{policy.id}</option>
                        ))}
                    </select>
                    <button
                        onClick={() => onAttachPolicy(agent.id, effectivePolicyId)}
                        disabled={busy || !effectivePolicyId}
                        className="px-3 py-2 rounded-lg bg-indigo-600/80 text-white text-xs font-semibold hover:bg-indigo-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Attach Policy
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto border border-white/5 rounded-xl">
                <table className="w-full text-left border-collapse min-w-[820px]">
                    <thead className="bg-slate-950/50">
                        <tr>
                            <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">Effect</th>
                            <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">Function</th>
                            <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">Condition</th>
                            <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">Policy / Statement</th>
                            <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {statements.map((statement, statementIndex) => (
                            <tr key={`${statement.policy_id}-${statement.statement_id}-${statementIndex}`} className="hover:bg-white/5">
                                <td className="px-4 py-3"><EffectBadge effect={statement.effect} /></td>
                                <td className="px-4 py-3 text-sm text-slate-200 font-mono">
                                    {(statement.resources || []).map(normalizeResource).join(', ')}
                                </td>
                                <td className="px-4 py-3 text-xs text-slate-300 font-mono">
                                    {statement.condition || '-'}
                                </td>
                                <td className="px-4 py-3 text-xs text-slate-300">
                                    <div className="font-mono text-indigo-200">{statement.policy_id}</div>
                                    <div className="text-slate-500">{statement.statement_id}</div>
                                </td>
                                <td className="px-4 py-3">
                                    <button
                                        onClick={() => onDeleteStatement(statement.policy_id, statement.statement_id)}
                                        className="text-slate-400 hover:text-red-300 transition-colors disabled:opacity-50"
                                        disabled={busy}
                                        title="Delete statement"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {statements.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-4 py-8 text-center text-slate-500 text-sm">
                                    No explicit statements. This principal is fully denied by default.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </Motion.div>
    );
};

const PlatformAccess = ({ accessControl, refreshData }) => {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [policyForm, setPolicyForm] = useState({ policy_id: "", name: "", description: "" });
    const [statementForm, setStatementForm] = useState({
        policy_id: "",
        effect: "ALLOW",
        resource: "",
        condition: "",
        risk_level: "low",
    });
    const [attachForm, setAttachForm] = useState({
        agent_id: "",
        agent_name: "",
        policy_id: "",
    });

    const runMutation = async (mutation, successMessage) => {
        setBusy(true);
        setError("");
        setSuccess("");
        try {
            await mutation();
            await refreshData();
            setSuccess(successMessage);
        } catch (mutationError) {
            setError(getErrorMessage(mutationError));
        } finally {
            setBusy(false);
        }
    };

    const agents = accessControl?.agents ?? EMPTY_LIST;
    const functions = accessControl?.functions ?? EMPTY_LIST;
    const policies = accessControl?.policies ?? EMPTY_LIST;
    const defaultPolicyId = policies[0]?.id || "";
    const defaultResourceId = functions[0]?.id || "";

    const functionOptions = useMemo(
        () => functions.map((fn) => ({ value: fn.id, label: fn.tool_name || fn.id })),
        [functions]
    );

    if (!accessControl) {
        return (
            <div className="glass-panel rounded-2xl p-10 flex items-center gap-4">
                <ShieldCheck className="w-6 h-6 text-indigo-300" />
                <p className="text-slate-300">Loading access-control model...</p>
            </div>
        );
    }

    const submitCreatePolicy = async () => {
        if (!policyForm.policy_id.trim() || !policyForm.name.trim()) {
            setError("Policy ID and policy name are required.");
            return;
        }
        await runMutation(
            () => api.post(`${API_BASE}/policies`, policyForm),
            `Created policy '${policyForm.policy_id}'.`
        );
        setPolicyForm({ policy_id: "", name: "", description: "" });
    };

    const submitAddStatement = async () => {
        const policyId = statementForm.policy_id || defaultPolicyId;
        const resource = statementForm.resource || defaultResourceId;
        if (!policyId || !resource) {
            setError("Select a policy and function before adding a statement.");
            return;
        }

        await runMutation(
            () => api.post(`${API_BASE}/statements`, {
                policy_id: policyId,
                effect: statementForm.effect,
                resources: [resource],
                actions: ["invoke"],
                condition: statementForm.condition || null,
                risk_level: statementForm.risk_level,
            }),
            `Added ${statementForm.effect} statement to '${policyId}'.`
        );
        setStatementForm((prev) => ({ ...prev, condition: "", resource: resource, policy_id: policyId }));
    };

    const submitAttachPolicy = async () => {
        const policyId = attachForm.policy_id || defaultPolicyId;
        if (!attachForm.agent_id.trim() || !policyId) {
            setError("Agent ID and policy are required to attach.");
            return;
        }

        await runMutation(
            () => api.post(`${API_BASE}/agents/attach-policy`, {
                agent_id: attachForm.agent_id.trim(),
                agent_name: attachForm.agent_name.trim() || null,
                policy_id: policyId,
            }),
            `Attached '${policyId}' to '${attachForm.agent_id}'.`
        );
        setAttachForm((prev) => ({ ...prev, agent_name: "" }));
    };

    const detachPolicy = async (agentId, policyId) => {
        await runMutation(
            () => api.post(`${API_BASE}/agents/detach-policy`, { agent_id: agentId, policy_id: policyId }),
            `Detached '${policyId}' from '${agentId}'.`
        );
    };

    const deleteStatement = async (policyId, statementId) => {
        await runMutation(
            () => api.delete(`${API_BASE}/policies/${policyId}/statements/${statementId}`),
            `Deleted '${statementId}' from '${policyId}'.`
        );
    };

    const attachPolicyToAgent = async (agentId, policyId) => {
        if (!policyId) return;
        await runMutation(
            () => api.post(`${API_BASE}/agents/attach-policy`, { agent_id: agentId, policy_id: policyId }),
            `Attached '${policyId}' to '${agentId}'.`
        );
    };

    const removeAgent = async (agentId) => {
        if (!agentId || agentId === "*") return;
        const confirmed = window.confirm(`Remove agent '${agentId}' from Access Management?`);
        if (!confirmed) return;

        await runMutation(
            () => api.post(`${API_BASE}/agents/remove`, { agent_id: agentId }),
            `Removed agent '${agentId}'.`
        );
    };

    const deletePolicy = async (policyId) => {
        if (!policyId) return;
        const attachedAgents = agents.filter((agent) => (agent.attached_policies || []).includes(policyId));
        const attachmentMessage = attachedAgents.length > 0
            ? ` It is currently attached to ${attachedAgents.length} agent(s) and will be detached automatically.`
            : "";
        const confirmed = window.confirm(
            `Delete policy '${policyId}'? This removes all statements in the policy.${attachmentMessage}`
        );
        if (!confirmed) return;

        await runMutation(
            () => api.delete(`${API_BASE}/policies/${encodeURIComponent(policyId)}`),
            `Deleted policy '${policyId}'.`
        );
    };

    return (
        <div className="space-y-6">
            <Motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel rounded-2xl p-6 border border-white/5"
            >
                <div className="flex flex-wrap gap-6 items-center">
                    <div className="flex items-center gap-3">
                        <Lock className="w-5 h-5 text-red-300" />
                        <div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Default Effect</p>
                            <p className="text-sm text-white font-semibold">{accessControl.default_effect}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <ShieldCheck className="w-5 h-5 text-indigo-300" />
                        <div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Policies</p>
                            <p className="text-sm text-white font-semibold">{policies.length}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <CircleCheck className="w-5 h-5 text-emerald-300" />
                        <div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Functions</p>
                            <p className="text-sm text-white font-semibold">{functions.length}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <ShieldAlert className="w-5 h-5 text-amber-300" />
                        <div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Agents</p>
                            <p className="text-sm text-white font-semibold">{agents.length}</p>
                        </div>
                    </div>
                </div>
                <p className="text-xs text-slate-400 mt-4">
                    Enforcement order: Explicit DENY {`>`} REVIEW {`>`} ALLOW. If no statement matches, request is denied.
                </p>
            </Motion.div>

            <Motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel rounded-2xl p-6 border border-white/5 space-y-5"
            >
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <h3 className="text-white font-semibold text-lg">Policy Editor</h3>
                    {busy && <span className="text-xs text-slate-400">Saving changes...</span>}
                </div>

                {error && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 px-3 py-2 rounded-lg">{error}</div>}
                {success && <div className="text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 px-3 py-2 rounded-lg">{success}</div>}

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <div className="bg-slate-950/40 border border-white/5 rounded-xl p-4 space-y-3">
                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Create Policy</p>
                        <input
                            value={policyForm.policy_id}
                            onChange={(event) => setPolicyForm((prev) => ({ ...prev, policy_id: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="policy_id (e.g. policy-finance-readonly)"
                        />
                        <input
                            value={policyForm.name}
                            onChange={(event) => setPolicyForm((prev) => ({ ...prev, name: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="Policy name"
                        />
                        <input
                            value={policyForm.description}
                            onChange={(event) => setPolicyForm((prev) => ({ ...prev, description: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="Optional description"
                        />
                        <button
                            onClick={submitCreatePolicy}
                            className="w-full px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition disabled:opacity-50"
                            disabled={busy}
                        >
                            <span className="inline-flex items-center gap-2"><Plus className="w-4 h-4" />Create Policy</span>
                        </button>
                        <div className="pt-3 border-t border-white/10 space-y-2">
                            <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Existing Policies</p>
                            <div className="max-h-44 overflow-y-auto space-y-2 pr-1">
                                {policies.length === 0 && (
                                    <p className="text-xs text-slate-500">No policies found.</p>
                                )}
                                {policies.map((policy) => {
                                    const attachedCount = agents.filter(
                                        (agent) => (agent.attached_policies || []).includes(policy.id)
                                    ).length;
                                    return (
                                        <div
                                            key={policy.id}
                                            className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-slate-900/40 px-2.5 py-2"
                                        >
                                            <div className="min-w-0">
                                                <p className="text-xs text-slate-200 font-mono truncate">{policy.id}</p>
                                                <p className="text-[10px] text-slate-500">
                                                    {policy.statements?.length || 0} stmt • {attachedCount} agent
                                                </p>
                                            </div>
                                            <button
                                                onClick={() => deletePolicy(policy.id)}
                                                className="text-slate-400 hover:text-red-300 transition-colors disabled:opacity-50"
                                                disabled={busy}
                                                title="Delete policy"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    <div className="bg-slate-950/40 border border-white/5 rounded-xl p-4 space-y-3">
                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Add Statement</p>
                        <select
                            value={statementForm.policy_id}
                            onChange={(event) => setStatementForm((prev) => ({ ...prev, policy_id: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                        >
                            <option value="">{defaultPolicyId ? "Select policy" : "No policies available"}</option>
                            {policies.map((policy) => (
                                <option key={policy.id} value={policy.id}>{policy.id}</option>
                            ))}
                        </select>
                        <div className="grid grid-cols-2 gap-2">
                            <select
                                value={statementForm.effect}
                                onChange={(event) => setStatementForm((prev) => ({ ...prev, effect: event.target.value }))}
                                className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            >
                                <option value="ALLOW">ALLOW</option>
                                <option value="REVIEW">REVIEW</option>
                                <option value="DENY">DENY</option>
                            </select>
                            <select
                                value={statementForm.risk_level}
                                onChange={(event) => setStatementForm((prev) => ({ ...prev, risk_level: event.target.value }))}
                                className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            >
                                <option value="low">low</option>
                                <option value="medium">medium</option>
                                <option value="high">high</option>
                                <option value="critical">critical</option>
                            </select>
                        </div>
                        <select
                            value={statementForm.resource}
                            onChange={(event) => setStatementForm((prev) => ({ ...prev, resource: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                        >
                            <option value="">{defaultResourceId ? "Select function" : "No functions available"}</option>
                            {functionOptions.map((option) => (
                                <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                        </select>
                        <input
                            value={statementForm.condition}
                            onChange={(event) => setStatementForm((prev) => ({ ...prev, condition: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="Condition (optional), e.g. path contains '/etc/shadow'"
                        />
                        <button
                            onClick={submitAddStatement}
                            className="w-full px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition disabled:opacity-50"
                            disabled={busy || policies.length === 0}
                        >
                            <span className="inline-flex items-center gap-2"><Plus className="w-4 h-4" />Add Statement</span>
                        </button>
                    </div>

                    <div className="bg-slate-950/40 border border-white/5 rounded-xl p-4 space-y-3">
                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Attach Policy to Agent</p>
                        <input
                            value={attachForm.agent_id}
                            onChange={(event) => setAttachForm((prev) => ({ ...prev, agent_id: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="Agent ID (existing or new)"
                        />
                        <input
                            value={attachForm.agent_name}
                            onChange={(event) => setAttachForm((prev) => ({ ...prev, agent_name: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                            placeholder="Agent name (optional)"
                        />
                        <select
                            value={attachForm.policy_id}
                            onChange={(event) => setAttachForm((prev) => ({ ...prev, policy_id: event.target.value }))}
                            className="w-full bg-slate-900/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-100"
                        >
                            <option value="">{defaultPolicyId ? "Select policy" : "No policies available"}</option>
                            {policies.map((policy) => (
                                <option key={policy.id} value={policy.id}>{policy.id}</option>
                            ))}
                        </select>
                        <button
                            onClick={submitAttachPolicy}
                            className="w-full px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition disabled:opacity-50"
                            disabled={busy || policies.length === 0}
                        >
                            <span className="inline-flex items-center gap-2"><Plus className="w-4 h-4" />Attach Policy</span>
                        </button>
                    </div>
                </div>
            </Motion.div>

            {agents.length === 0 && (
                <div className="glass-panel rounded-2xl p-10 text-slate-400">
                    No agent principals are configured yet.
                </div>
            )}

            <div className="space-y-4">
                {agents.map((agent, index) => (
                    <AgentCard
                        key={agent.id}
                        agent={agent}
                        index={index}
                        allPolicies={policies}
                        busy={busy}
                        onAttachPolicy={attachPolicyToAgent}
                        onDetachPolicy={detachPolicy}
                        onDeleteStatement={deleteStatement}
                        onRemoveAgent={removeAgent}
                    />
                ))}
            </div>
        </div>
    );
};

export default PlatformAccess;
