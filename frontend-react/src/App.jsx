import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ActionCenter from './components/ActionCenter';
import AuditLog from './components/AuditLog';
import PlatformAccess from './components/PlatformAccess';
import ConfigurationModal from './components/ConfigurationModal';
import { Trash2, Settings } from 'lucide-react';
import { api } from './api';
import { DEFAULT_RISK_CONFIG } from './constants/riskConfig';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [requests, setRequests] = useState([]);
  const [stats, setStats] = useState({ total_requests: 0, total_pending: 0, total_blocked: 0 });
  const [accessControl, setAccessControl] = useState(null);

  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [riskConfig, setRiskConfig] = useState(DEFAULT_RISK_CONFIG);

  const fetchData = async () => {
    try {
      const [requestsResponse, statsResponse, accessControlResponse] = await Promise.all([
        api.get('/api/requests'),
        api.get('/api/stats'),
        api.get('/api/access-control'),
      ]);
      setRequests(requestsResponse.data);
      setStats(statsResponse.data);
      setAccessControl(accessControlResponse.data);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  useEffect(() => {
    const kickoff = setTimeout(() => {
      fetchData();
    }, 0);
    const interval = setInterval(fetchData, 2000);
    return () => {
      clearTimeout(kickoff);
      clearInterval(interval);
    };
  }, []);

  const handleReset = async () => {
    if (window.confirm("Are you sure you want to reset the system? This will delete all request history.")) {
      try {
        await api.post('/api/reset');
        fetchData(); // Refresh immediately
      } catch (error) {
        console.error("Error resetting system:", error);
      }
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard requests={requests} stats={stats} riskConfig={riskConfig} />;
      case 'actions': return <ActionCenter requests={requests} refreshData={fetchData} />;
      case 'audit': return <AuditLog requests={requests} />;
      case 'platform': return <PlatformAccess accessControl={accessControl} refreshData={fetchData} />;
      default: return <Dashboard requests={requests} stats={stats} riskConfig={riskConfig} />;
    }
  };

  const headerTitle = {
    dashboard: 'Overview',
    actions: 'Action Center',
    audit: 'System Logs',
    platform: 'Platform Access',
  }[activeTab] || 'Overview';

  return (
    <div className="flex h-screen w-full text-slate-200 font-sans overflow-hidden relative">
      {/* Ambient Background Effects */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-indigo-900/20 rounded-full blur-[128px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-blue-900/20 rounded-full blur-[128px]" />
      </div>

      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 flex flex-col relative z-10 h-full overflow-hidden">
        <header className="border-b border-white/5 bg-slate-950/50 backdrop-blur-sm sticky top-0 z-20">
          <div className="flex items-center justify-between w-full max-w-7xl mx-auto px-6 py-6">
            <div>
              <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                {headerTitle}
              </h1>
              <p className="text-sm text-slate-400 mt-1">Real-time governance monitoring</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsConfigOpen(true)}
                className="px-5 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all text-sm font-medium border border-white/5 flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                <span>Configuration</span>
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 hover:text-red-300 transition-all text-sm font-medium"
              >
                <Trash2 className="w-4 h-4" />
                <span>Reset System</span>
              </button>
              <div className="flex items-center gap-2 bg-white/5 px-4 py-2 rounded-full border border-white/5">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                <span className="text-sm font-medium text-emerald-400">System Online</span>
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto scroll-smooth">
          <div className="w-full max-w-7xl mx-auto px-6 pt-8 pb-12">
            {renderContent()}
          </div>
        </div>

        {isConfigOpen && (
          <ConfigurationModal
            onClose={() => setIsConfigOpen(false)}
            config={riskConfig}
            onSave={setRiskConfig}
          />
        )}
      </main>
    </div>
  );
}

export default App;
