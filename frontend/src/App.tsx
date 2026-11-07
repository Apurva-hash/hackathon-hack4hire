import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { Login } from './pages/Login';

// Admin Pages
import { Overview } from './pages/admin/Overview';
import { LiveMap } from './pages/admin/LiveMap';
import { Jobs } from './pages/admin/Jobs';
import { Escalations } from './pages/admin/Escalations';
import { Technicians } from './pages/admin/Technicians';
import { Customers } from './pages/admin/Customers';
import { Feedback } from './pages/admin/Feedback';
import { Reports } from './pages/admin/Reports';
import { Settings } from './pages/admin/Settings';
import { AuditHistory } from './pages/admin/AuditHistory';
import { Scheduling } from './pages/admin/Scheduling';
import { Optimization } from './pages/admin/Optimization';
import { Disruptions } from './pages/admin/Disruptions';
import { Explainability } from './pages/admin/Explainability';

// Customer Pages
import { MyBookings } from './pages/customer/MyBookings';
import { BookService } from './pages/customer/BookService';
import { CustomerHistory } from './pages/customer/CustomerHistory';
import { CustomerProfile } from './pages/customer/CustomerProfile';

// Technician Pages
import { MySchedule } from './pages/technician/MySchedule';
import { JobHistory } from './pages/technician/JobHistory';
import { Earnings } from './pages/technician/Earnings';
import { TechnicianProfile } from './pages/technician/TechnicianProfile';
import { ReportDisruption } from './pages/technician/ReportDisruption';

const RootRedirect: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  if (user.role === 'admin') return <Navigate to="/admin/overview" replace />;
  if (user.role === 'technician') return <Navigate to="/technician/dashboard" replace />;
  if (user.role === 'customer') return <Navigate to="/customer/dashboard" replace />;
  return <Navigate to="/login" replace />;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RootRedirect />} />

          {/* Admin Routes */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="dashboard" element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<Overview />} />
            <Route path="live-map" element={<LiveMap />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="escalations" element={<Escalations />} />
            <Route path="technicians" element={<Technicians />} />
            <Route path="customers" element={<Customers />} />
            <Route path="feedback" element={<Feedback />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit" element={<AuditHistory />} />
            {/* Backward-compatible legacy routes */}
            <Route path="scheduling" element={<Scheduling />} />
            <Route path="optimization" element={<Optimization />} />
            <Route path="disruptions" element={<Disruptions />} />
            <Route path="explainability" element={<Explainability />} />
          </Route>

          {/* Customer Routes */}
          <Route
            path="/customer"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<MyBookings />} />
            <Route path="book" element={<BookService />} />
            <Route path="history" element={<CustomerHistory />} />
            <Route path="profile" element={<CustomerProfile />} />
          </Route>

          {/* Technician Routes */}
          <Route
            path="/technician"
            element={
              <ProtectedRoute allowedRoles={['technician']}>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<MySchedule />} />
            <Route path="history" element={<JobHistory />} />
            <Route path="earnings" element={<Earnings />} />
            <Route path="profile" element={<TechnicianProfile />} />
            <Route path="disruption" element={<ReportDisruption />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
