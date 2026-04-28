import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AppLayout } from './components/layout/AppLayout';

// View Stubs (to be implemented)
import MembersView from './views/MembersView';
import PoliciesView from './views/PoliciesView';
import ClaimsView from './views/ClaimsView';
import DisputesView from './views/DisputesView';

function App() {
  return (
    <AppProvider>
      <Router>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/members" replace />} />
            <Route path="members" element={<MembersView />} />
            <Route path="policies" element={<PoliciesView />} />
            <Route path="claims" element={<ClaimsView />} />
            <Route path="disputes" element={<DisputesView />} />
            <Route path="*" element={<Navigate to="/members" replace />} />
          </Route>
        </Routes>
      </Router>
    </AppProvider>
  );
}

export default App;
