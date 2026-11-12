import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { StoreProvider } from './contexts/StoreContext';
import { ToastProvider } from './contexts/ToastContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ProtectedRoute from './utils/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Chat from './pages/Chat';
import Orders from './pages/Orders';
import Analytics from './pages/Analytics';
import WidgetSettings from './pages/WidgetSettings';
import Settings from './pages/Settings';
import Stores from './pages/Stores';
import Buyers from './pages/Buyers';
import Collections from './pages/Collections';
import Catalog from './pages/Catalog';
import SeoMarketplace from './pages/SeoMarketplace';
import Governance from './pages/Governance';
import AISessions from './pages/AISessions';
import AISessionDetail from './pages/AISessionDetail';
import NotFound from './pages/NotFound';
import DashboardLayout from './components/layout/DashboardLayout';

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <StoreProvider>
              <ErrorBoundary>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  <Route path="/reset-password" element={<ResetPassword />} />
                  <Route element={<ProtectedRoute />}>
                    <Route element={<DashboardLayout />}>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/products" element={<Products />} />
                      <Route path="/orders" element={<Orders />} />
                      <Route path="/conversations" element={<Chat />} />
                      <Route path="/analytics" element={<Analytics />} />
                      <Route path="/widget" element={<WidgetSettings />} />
                      <Route path="/stores" element={<Stores />} />
                      <Route path="/buyers" element={<Buyers />} />
                      <Route path="/collections" element={<Collections />} />
                      <Route path="/catalog" element={<Catalog />} />
                      <Route path="/seo" element={<SeoMarketplace />} />
                      <Route path="/governance" element={<Governance />} />
                      <Route path="/ai-sessions" element={<AISessions />} />
                      <Route path="/ai-sessions/:id" element={<AISessionDetail />} />
                      <Route path="/settings" element={<Settings />} />
                    </Route>
                  </Route>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </ErrorBoundary>
            </StoreProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
