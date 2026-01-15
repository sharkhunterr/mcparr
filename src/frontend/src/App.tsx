import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Services from './pages/Services';
import Users from './pages/Users';
import Configuration from './pages/Configuration';
import Monitoring from './pages/Monitoring';
import MCP from './pages/MCP';
import Training from './pages/Training';
import Help from './pages/Help';
import Wizard from './components/Wizard';
import { logger } from './lib/logger';
import { ThemeProvider } from './contexts/ThemeContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { WizardProvider, useWizard } from './contexts/WizardContext';
import './i18n';

function AppRoutes() {
  const { state } = useWizard();

  // If wizard not completed, redirect to wizard
  if (!state.hasCompletedWizard) {
    return (
      <Routes>
        <Route path="/wizard" element={<Wizard />} />
        <Route path="*" element={<Navigate to="/wizard" replace />} />
      </Routes>
    );
  }

  // Normal routes after wizard completion
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/services" element={<Services />} />
        <Route path="/users" element={<Users />} />
        <Route path="/mcp" element={<MCP />} />
        <Route path="/training" element={<Training />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/configuration" element={<Configuration />} />
        <Route path="/help" element={<Help />} />
        <Route path="/wizard" element={<Wizard />} />
        <Route path="*" element={<div className="p-6">404 - Page Not Found</div>} />
      </Routes>
    </Layout>
  );
}

function App() {
  useEffect(() => {
    logger.info('Application started', 'app', {
      userAgent: navigator.userAgent,
      url: window.location.href,
    });
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <SettingsProvider>
          <WizardProvider>
            <Router>
              <AppRoutes />
            </Router>
          </WizardProvider>
        </SettingsProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
