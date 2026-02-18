/**
 * FSC Policy RAG System - Main App with Dashboard Layout.
 */
import { useState } from 'react';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import MonitorDashboard from './sections/MonitorDashboard';
import TopicMap from './sections/TopicMap';
import IndustryPanel from './sections/IndustryPanel';
import NewQASection from './sections/NewQASection';
import ChecklistGenerator from './sections/ChecklistGenerator';
import QualityDashboard from './sections/QualityDashboard';
import { Toaster } from '@/components/ui/sonner';

function App() {
  const [activeSection, setActiveSection] = useState('monitor');

  const renderSection = () => {
    switch (activeSection) {
      case 'monitor':
        return <MonitorDashboard />;
      case 'topics':
        return <TopicMap />;
      case 'industry':
        return <IndustryPanel />;
      case 'qa':
        return <NewQASection />;
      case 'checklist':
        return <ChecklistGenerator />;
      case 'quality':
        return <QualityDashboard />;
      default:
        return <MonitorDashboard />;
    }
  };

  return (
    <DashboardLayout 
      activeSection={activeSection} 
      onSectionChange={setActiveSection}
    >
      {renderSection()}
      <Toaster />
    </DashboardLayout>
  );
}

export default App;
