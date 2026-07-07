/** App Router — alle Seiten und Routen. */

import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { isAuthenticated } from './lib/auth';
import { Appointments } from './pages/Appointments';
import { Conversations } from './pages/Conversations';
import { Costs } from './pages/Costs';
import { Dashboard } from './pages/Dashboard';
import { Feedback } from './pages/Feedback';
import { FollowUps } from './pages/FollowUps';
import { Knowledge } from './pages/Knowledge';
import { LeadDetail } from './pages/LeadDetail';
import { Leads } from './pages/Leads';
import { Login } from './pages/Login';
import { Settings } from './pages/Settings';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="leads/:id" element={<LeadDetail />} />
        <Route path="conversations" element={<Conversations />} />
        <Route path="costs" element={<Costs />} />
        <Route path="appointments" element={<Appointments />} />
        <Route path="followups" element={<FollowUps />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="feedback" element={<Feedback />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
