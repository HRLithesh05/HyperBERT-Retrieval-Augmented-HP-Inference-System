import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { CustomCursor } from './components/CustomCursor';
import { ThemeProvider } from './components/ThemeProvider';
import { NavBar } from './components/NavBar';
import { SessionProvider, useSession } from './contexts/SessionContext';
import { auth0Config, isAuthConfigured } from './lib/auth0-config';
import AuthGate from './components/AuthGate';
import Landing from './pages/Landing';
import UploadProcess from './pages/UploadProcess';
import ResultsDashboard from './pages/ResultsDashboard';
import CorpusExplorer from './pages/CorpusExplorer';
import ComparisonDashboard from './pages/ComparisonDashboard';
import EvaluationDashboard from './pages/EvaluationDashboard';
import NotebookViewer from './pages/NotebookViewer';
import Methodology from './pages/Methodology';
import History from './pages/History';

/** Redirect /results (no id) to the last active session or upload page */
function ResultsRedirect() {
  const { sessionId, hasRealSession } = useSession();
  if (hasRealSession) return <Navigate to={`/results/${sessionId}`} replace />;
  return <Navigate to="/upload" replace />;
}

/** Conditionally wrap children with Auth0Provider */
function AuthWrapper({ children }: { children: React.ReactNode }) {
  if (!isAuthConfigured) return <>{children}</>;
  return (
    <Auth0Provider
      domain={auth0Config.domain}
      clientId={auth0Config.clientId}
      authorizationParams={auth0Config.authorizationParams}
    >
      {children}
    </Auth0Provider>
  );
}

function App() {
  return (
    <ThemeProvider defaultTheme="dark">
      <AuthWrapper>
        <SessionProvider>
          <Router>
            <CustomCursor />
            <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
              <NavBar />
              <main style={{ flex: 1 }}>
                <Routes>
                  <Route path="/" element={<Landing />} />
                  <Route path="/upload" element={<UploadProcess />} />
                  <Route path="/results" element={<ResultsRedirect />} />
                  <Route path="/results/:id" element={<ResultsDashboard />} />
                  <Route path="/compare/:id" element={<ComparisonDashboard />} />
                  <Route path="/notebook/:id" element={
                    <AuthGate feature="Running Jupyter notebooks">
                      <NotebookViewer />
                    </AuthGate>
                  } />
                  <Route path="/corpus" element={<CorpusExplorer />} />
                  <Route path="/evaluation" element={<EvaluationDashboard />} />
                  <Route path="/methodology" element={<Methodology />} />
                  <Route path="/history" element={
                    <AuthGate feature="Viewing analysis history">
                      <History />
                    </AuthGate>
                  } />
                </Routes>
              </main>
            </div>
          </Router>
        </SessionProvider>
      </AuthWrapper>
    </ThemeProvider>
  );
}

export default App;
