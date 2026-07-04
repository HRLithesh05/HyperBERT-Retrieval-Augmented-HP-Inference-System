import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CustomCursor } from './components/CustomCursor';
import { ThemeProvider } from './components/ThemeProvider';
import { NavBar } from './components/NavBar';
import { SessionProvider } from './contexts/SessionContext';
import Landing from './pages/Landing';
import UploadProcess from './pages/UploadProcess';
import ResultsDashboard from './pages/ResultsDashboard';
import CorpusExplorer from './pages/CorpusExplorer';
import ComparisonDashboard from './pages/ComparisonDashboard';
import EvaluationDashboard from './pages/EvaluationDashboard';
import NotebookViewer from './pages/NotebookViewer';
import Methodology from './pages/Methodology';

function App() {
  return (
    <ThemeProvider defaultTheme="dark">
      <SessionProvider>
        <Router>
          <CustomCursor />
          <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
            <NavBar />
            <main style={{ flex: 1 }}>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/upload" element={<UploadProcess />} />
                <Route path="/results/:id" element={<ResultsDashboard />} />
                <Route path="/results" element={<ResultsDashboard />} />
                <Route path="/compare/:id" element={<ComparisonDashboard />} />
                <Route path="/compare" element={<ComparisonDashboard />} />
                <Route path="/notebook/:id" element={<NotebookViewer />} />
                <Route path="/notebook" element={<NotebookViewer />} />
                <Route path="/corpus" element={<CorpusExplorer />} />
                <Route path="/evaluation" element={<EvaluationDashboard />} />
                <Route path="/methodology" element={<Methodology />} />
              </Routes>
            </main>
          </div>
        </Router>
      </SessionProvider>
    </ThemeProvider>
  );
}

export default App;
