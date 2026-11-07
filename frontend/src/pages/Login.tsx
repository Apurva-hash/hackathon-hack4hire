import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Modal } from '../components/common/Modal';
import { SunIcon, MoonIcon, WrenchIcon } from '../components/common/Icons';
import { api } from '../services/apiClient';

export const Login: React.FC = () => {
  const { login, quickLogin, registerCustomer, registerTechnician, isDarkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<'login' | 'registerCustomer' | 'registerTechnician'>('login');
  const [selectedRole, setSelectedRole] = useState<UserRole>('customer');

  // Form fields
  const [email, setEmail] = useState('alice@example.com');
  const [password, setPassword] = useState('Customer@1234');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [certLevel, setCertLevel] = useState<number>(3);
  const [radiusKm, setRadiusKm] = useState<number>(20);

  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Forgot Password modal
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

  const handleRoleSelect = (role: UserRole) => {
    setSelectedRole(role);
    setErrorMsg(null);
    if (role === 'admin') {
      setEmail('admin@dispatchgrid.dev');
      setPassword('Admin@1234');
    } else if (role === 'technician') {
      setEmail('raj.tech@example.com');
      setPassword('Tech@1234');
    } else {
      setEmail('alice@example.com');
      setPassword('Customer@1234');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const user = await login(email, password);
        if (user.role === 'admin') navigate('/admin/overview');
        else if (user.role === 'technician') navigate('/technician/dashboard');
        else navigate('/customer/dashboard');
      } else if (mode === 'registerCustomer') {
        await registerCustomer({ email, password, name, phone });
        setSuccessMsg('Account registered successfully! Logging you in...');
        setTimeout(() => {
          navigate('/customer/dashboard');
        }, 1000);
      } else if (mode === 'registerTechnician') {
        const res = await registerTechnician({
          email,
          password,
          name,
          phone,
          certification_level: certLevel,
          service_radius_km: radiusKm,
        });
        setSuccessMsg(res.message || 'Technician registered! Awaiting admin approval.');
        setTimeout(() => {
          navigate('/technician/dashboard');
        }, 1500);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (role: UserRole) => {
    setErrorMsg(null);
    setLoading(true);
    try {
      const user = await quickLogin(role);
      if (user.role === 'admin') navigate('/admin/overview');
      else if (user.role === 'technician') navigate('/technician/dashboard');
      else navigate('/customer/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Quick login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col justify-center items-center p-4 relative selection:bg-primary-tint">
      {/* Top right dark mode toggle */}
      <div className="absolute top-4 right-4">
        <button
          onClick={toggleDarkMode}
          aria-label={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className="p-2.5 rounded-full bg-surface border border-border text-text hover:bg-surface-alt transition-colors shadow-warmSm min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          {isDarkMode ? <SunIcon size={20} className="text-accent" /> : <MoonIcon size={20} />}
        </button>
      </div>

      <div className="max-w-md w-full bg-surface text-text rounded-modal shadow-warmXl p-6 sm:p-8 border border-border">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex w-12 h-12 rounded-xl bg-primary text-white items-center justify-center shadow-warmSm mb-3">
            <WrenchIcon size={24} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text">DispatchGrid</h1>
          <p className="text-xs text-text-muted mt-1">
            Intelligent Workforce Scheduling & On-Demand Service Platform
          </p>
        </div>

        {/* Mode Toggle (Sign In / Register) */}
        <div className="flex border-b border-border mb-5">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setErrorMsg(null);
            }}
            className={`flex-1 py-2 text-xs font-bold border-b-2 transition-colors ${
              mode === 'login'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('registerCustomer');
              setErrorMsg(null);
            }}
            className={`flex-1 py-2 text-xs font-bold border-b-2 transition-colors ${
              mode === 'registerCustomer'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            New Customer
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('registerTechnician');
              setErrorMsg(null);
            }}
            className={`flex-1 py-2 text-xs font-bold border-b-2 transition-colors ${
              mode === 'registerTechnician'
                ? 'border-primary text-primary'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            Join as Tech
          </button>
        </div>

        {/* Role Select Buttons if in Login mode */}
        {mode === 'login' && (
          <div className="mb-5">
            <label className="block text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2">
              Select Demo Persona
            </label>
            <div className="grid grid-cols-3 gap-2 p-1 bg-surface-alt rounded-input border border-border">
              {(['customer', 'technician', 'admin'] as UserRole[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => handleRoleSelect(r)}
                  className={`py-2 text-xs font-bold rounded-lg transition-all capitalize ${
                    selectedRole === r
                      ? 'bg-primary text-white shadow-warmSm'
                      : 'text-text-muted hover:text-text'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error or Success notification */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-card bg-status-error/10 border border-status-error/30 text-xs text-status-error font-medium">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-3 rounded-card bg-status-success/10 border border-status-success/30 text-xs text-status-success font-medium">
            {successMsg}
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {(mode === 'registerCustomer' || mode === 'registerTechnician') && (
            <Input
              label="Full Name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. John Doe"
            />
          )}

          <Input
            label="Email Address"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
          />

          {(mode === 'registerCustomer' || mode === 'registerTechnician') && (
            <Input
              label="Phone Number"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
            />
          )}

          {mode === 'registerTechnician' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Cert Level (1-5)
                </label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={certLevel}
                  onChange={(e) => setCertLevel(parseInt(e.target.value) || 1)}
                  className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Radius (km)
                </label>
                <input
                  type="number"
                  min="5"
                  max="50"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(parseFloat(e.target.value) || 15)}
                  className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
                />
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-text uppercase tracking-wider">
                Password
              </label>
              {mode === 'login' && (
                <button
                  type="button"
                  onClick={() => setForgotModalOpen(true)}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Forgot password?
                </button>
              )}
            </div>
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-2"
          >
            {mode === 'login'
              ? `Sign In as ${selectedRole.toUpperCase()}`
              : mode === 'registerCustomer'
              ? 'Create Customer Account'
              : 'Submit Technician Registration'}
          </Button>
        </form>

        {/* 1-Click Instant Demo Logins */}
        {mode === 'login' && (
          <div className="mt-6 pt-5 border-t border-border">
            <div className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2.5 text-center">
              1-Click Demo Logins
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('customer')}
                className="p-2.5 border border-border bg-surface-alt hover:bg-border/60 text-text rounded-card text-left transition text-xs shadow-warmSm min-h-[44px]"
              >
                <div className="font-bold text-primary">📦 Customer</div>
                <div className="text-[10px] text-text-muted">Alice Sharma</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('technician')}
                className="p-2.5 border border-border bg-surface-alt hover:bg-border/60 text-text rounded-card text-left transition text-xs shadow-warmSm min-h-[44px]"
              >
                <div className="font-bold text-status-progress">👷 Technician</div>
                <div className="text-[10px] text-text-muted">Raj Kumar (AC)</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('admin')}
                className="p-2.5 border border-border bg-surface-alt hover:bg-border/60 text-text rounded-card text-left transition text-xs shadow-warmSm min-h-[44px]"
              >
                <div className="font-bold text-accent">⚡ Admin</div>
                <div className="text-[10px] text-text-muted">Full Console</div>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Forgot Password Modal */}
      <Modal
        isOpen={forgotModalOpen}
        onClose={() => {
          setForgotModalOpen(false);
          setForgotSubmitted(false);
        }}
        title="Reset Your Password"
        description="Enter your registered email and we'll send you recovery instructions."
      >
        {forgotSubmitted ? (
          <div className="py-4 text-center">
            <div className="w-12 h-12 rounded-full bg-status-success/15 text-status-success mx-auto flex items-center justify-center mb-3">
              ✓
            </div>
            <h4 className="text-sm font-bold text-text">Recovery Link Sent</h4>
            <p className="text-xs text-text-muted mt-1">
              If an account exists for {forgotEmail}, a password reset link has been dispatched.
            </p>
            <Button
              variant="primary"
              size="md"
              className="mt-4"
              onClick={() => {
                setForgotModalOpen(false);
                setForgotSubmitted(false);
              }}
            >
              Back to Sign In
            </Button>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setForgotSubmitted(true);
            }}
            className="space-y-4 py-2"
          >
            <Input
              label="Email Address"
              type="email"
              required
              value={forgotEmail}
              onChange={(e) => setForgotEmail(e.target.value)}
              placeholder="you@example.com"
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setForgotModalOpen(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" size="md" type="submit">
                Send Reset Link
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};
