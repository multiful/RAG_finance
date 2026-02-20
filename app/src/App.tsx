/**
 * FSC Policy RAG System - Main App with Dashboard Layout.
 */
import { Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import MonitorDashboard from './sections/MonitorDashboard';
import TopicMap from './sections/TopicMap';
import IndustryPanel from './sections/IndustryPanel';
import NewQASection from './sections/NewQASection';
import ChecklistGenerator from './sections/ChecklistGenerator';
import QualityDashboard from './sections/QualityDashboard';
import PolicyTimeline from './sections/PolicyTimeline';
import { Toaster } from '@/components/ui/sonner';

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-20">
      <h2 className="text-2xl font-bold text-slate-900">404 - Page Not Found</h2>
      <p className="text-slate-500 mt-2">The page you are looking for does not exist.</p>
    </div>
  );
}

function App() {
  return (
    <DashboardLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/monitoring" replace />} />
        <Route path="/monitoring" element={<MonitorDashboard />} />
        <Route path="/radar" element={<TopicMap />} />
        <Route path="/industry" element={<IndustryPanel />} />
        <Route path="/workspace/qa" element={<NewQASection />} />
        <Route path="/workspace/checklist" element={<ChecklistGenerator />} />
        <Route path="/timeline" element={<PolicyTimeline />} />
        <Route path="/observability" element={<QualityDashboard />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <Toaster />
    </DashboardLayout>
  );
}

export default App;
