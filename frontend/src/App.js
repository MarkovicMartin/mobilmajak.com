import React from 'react';
import { BrowserRouter as Router, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import LoginForm from './components/LoginForm';
import Dashboard from './components/Dashboard';
import ScrollToTop from './components/ScrollToTop';
import ClarityPageTracker from './components/ClarityPageTracker';
import { rememberReturnPath, consumeReturnPath } from './utils/authReturnPath';
import './App.css';
import './styles/ui.css';

const AppContent = () => {
  const { user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const rememberedRef = React.useRef(false);
  const restoredRef = React.useRef(false);

  React.useEffect(() => {
    if (!user) {
      restoredRef.current = false;
      rememberedRef.current = false;
    }
  }, [user]);

  // Před loginem si zapamatuj deep-link (např. /tasks/manage?id=40)
  React.useEffect(() => {
    if (loading || user) return;
    if (rememberedRef.current) return;
    rememberedRef.current = true;
    rememberReturnPath(location.pathname, location.search);
  }, [loading, user, location.pathname, location.search]);

  // Po přihlášení skoč zpět na zapamatovanou cestu (kdyby URL zůstala na /)
  React.useEffect(() => {
    if (loading || !user || restoredRef.current) return;
    restoredRef.current = true;
    const target = consumeReturnPath();
    if (!target) return;
    const current = `${location.pathname}${location.search}`;
    if (target !== current) {
      navigate(target, { replace: true });
    }
  }, [loading, user, navigate, location.pathname, location.search]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Načítání...</p>
      </div>
    );
  }

  return user ? <Dashboard /> : <LoginForm />;
};

function App() {
  return (
    <Router>
      <ScrollToTop />
      <ThemeProvider>
        <AuthProvider>
          <ClarityPageTracker />
          <div className="App">
            <AppContent />
          </div>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
