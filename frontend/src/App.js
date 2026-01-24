import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// API Helper
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for cookies
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth Context
const AuthContext = React.createContext();

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // Check for JWT token or session cookie
    try {
      const response = await api.get('/api/auth/me');
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      setUser(null);
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    const response = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('token', response.data.access_token);
    setUser(response.data.user);
    return response.data;
  };

  const register = async (email, password, full_name, company_name) => {
    const response = await api.post('/api/auth/register', {
      email,
      password,
      full_name,
      company_name,
    });
    localStorage.setItem('token', response.data.access_token);
    setUser(response.data.user);
    return response.data;
  };

  const logout = async () => {
    try {
      await api.post('/api/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('token');
    setUser(null);
  };

  const setUserData = (userData) => {
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, checkAuth, setUserData }}>
      {children}
    </AuthContext.Provider>
  );
}

const useAuth = () => React.useContext(AuthContext);

// Protected Route Component
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" />;
}

// OAuth Callback Handler
function AuthCallback() {
  const navigate = useNavigate();
  const { setUserData } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.substring(1));
        const sessionId = params.get('session_id');

        if (!sessionId) {
          console.error('No session_id found');
          navigate('/login');
          return;
        }

        // Exchange session_id for user data
        const response = await api.post('/api/auth/oauth/session', null, {
          headers: {
            'X-Session-ID': sessionId,
          },
        });

        // Set user data
        setUserData(response.data);

        // Clear fragment and redirect to dashboard
        window.history.replaceState(null, '', '/dashboard');
        navigate('/dashboard', { replace: true, state: { user: response.data } });
      } catch (error) {
        console.error('OAuth session error:', error);
        navigate('/login');
      }
    };

    processSession();
  }, [navigate, setUserData]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-white">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto mb-4"></div>
        <p className="text-gray-600 text-lg">Completing sign in...</p>
      </div>
    </div>
  );
}

// Landing Page
function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/dashboard" />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white">
      {/* Header */}
      <header className="container mx-auto px-6 py-6">
        <nav className="flex justify-between items-center">
          <div className="text-2xl font-bold text-primary-600" data-testid="logo">MarketingOS</div>
          <div className="space-x-4">
            <button
              onClick={() => navigate('/login')}
              className="px-6 py-2 text-primary-600 hover:text-primary-700 font-medium"
              data-testid="login-nav-btn"
            >
              Login
            </button>
            <button
              onClick={() => navigate('/register')}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
              data-testid="signup-nav-btn"
            >
              Get Started
            </button>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20 text-center" data-testid="hero-section">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
          Supercharge Your <span className="text-primary-600">Marketing</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          AI-powered marketing platform for teams. Monitor your digital presence,
          get actionable insights, and execute strategies with your team.
        </p>
        <button
          onClick={() => navigate('/register')}
          className="px-8 py-4 bg-primary-600 text-white rounded-lg text-lg font-semibold hover:bg-primary-700 shadow-lg"
          data-testid="hero-cta-btn"
        >
          Start Free Trial
        </button>
      </section>

      {/* Features */}
      <section className="container mx-auto px-6 py-20" data-testid="features-section">
        <h2 className="text-3xl font-bold text-center mb-12">Everything You Need</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white p-8 rounded-xl shadow-md" data-testid="feature-analytics">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="text-xl font-semibold mb-3">Marketing Analytics</h3>
            <p className="text-gray-600">
              Track website traffic, keyword rankings, backlinks, and social media engagement in one place.
            </p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-md" data-testid="feature-ai">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold mb-3">AI-Powered Insights</h3>
            <p className="text-gray-600">
              Get personalized recommendations, generate content, and create stunning visuals with AI.
            </p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-md" data-testid="feature-collaboration">
            <div className="text-4xl mb-4">👥</div>
            <h3 className="text-xl font-semibold mb-3">Team Collaboration</h3>
            <p className="text-gray-600">
              Assign tasks, track progress, and collaborate with your team seamlessly.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="container mx-auto px-6 py-20 bg-gray-50 rounded-3xl my-12" data-testid="pricing-section">
        <h2 className="text-3xl font-bold text-center mb-4">Simple Pricing</h2>
        <p className="text-center text-gray-600 mb-12">Choose the plan that fits your team</p>
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {[
            {
              name: 'Starter',
              price: '$19',
              features: ['Up to 5 users', 'Basic analytics', 'AI copywriting', 'Email support'],
              testid: 'plan-starter'
            },
            {
              name: 'Professional',
              price: '$49',
              features: ['Up to 5 users', 'Advanced analytics', 'Full AI tools', 'Priority support'],
              popular: true,
              testid: 'plan-professional'
            },
            {
              name: 'Agency',
              price: '$99',
              features: ['Up to 5 users', 'Custom integrations', 'Unlimited AI', 'Dedicated support'],
              testid: 'plan-agency'
            },
          ].map((plan) => (
            <div
              key={plan.name}
              className={`bg-white p-8 rounded-xl shadow-md ${plan.popular ? 'ring-2 ring-primary-600' : ''}`}
              data-testid={plan.testid}
            >
              {plan.popular && (
                <span className="bg-primary-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                  Popular
                </span>
              )}
              <h3 className="text-2xl font-bold mt-4 mb-2">{plan.name}</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-gray-600">/month</span>
              </div>
              <ul className="space-y-3 mb-6">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-center">
                    <svg className="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => navigate('/register')}
                className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
                data-testid={`${plan.testid}-cta-btn`}
              >
                Get Started
              </button>
            </div>
          ))}
        </div>
        <p className="text-center text-sm text-gray-600 mt-8">
          +$10-20 per additional 5 users depending on plan
        </p>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-8 text-center text-gray-600">
        <p>&copy; 2025 MarketingOS. All rights reserved.</p>
      </footer>
    </div>
  );
}

// Login Page
function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-white px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8" data-testid="login-form">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Welcome Back</h2>
          <p className="text-gray-600 mt-2">Sign in to your account</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4" data-testid="login-error">
            {error}
          </div>
        )}

        {/* Google OAuth Button */}
        <button
          onClick={handleGoogleLogin}
          className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-300 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-50 mb-6"
          data-testid="google-login-btn"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Or continue with email</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="you@example.com"
              required
              data-testid="login-email-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="••••••••"
              required
              data-testid="login-password-input"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 text-white py-3 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            data-testid="login-submit-btn"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600 hover:text-primary-700 font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

// Register Page
function RegisterPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    company_name: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.full_name, formData.company_name);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignup = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-white px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8" data-testid="register-form">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Get Started</h2>
          <p className="text-gray-600 mt-2">Create your account</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4" data-testid="register-error">
            {error}
          </div>
        )}

        {/* Google OAuth Button */}
        <button
          onClick={handleGoogleSignup}
          className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-300 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-50 mb-6"
          data-testid="google-signup-btn"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Or continue with email</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="John Doe"
              required
              data-testid="register-name-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="you@example.com"
              required
              data-testid="register-email-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="••••••••"
              required
              minLength={6}
              data-testid="register-password-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company Name (Optional)
            </label>
            <input
              type="text"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
              placeholder="Acme Inc."
              data-testid="register-company-input"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 text-white py-3 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            data-testid="register-submit-btn"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

// Dashboard Page
function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm" data-testid="dashboard-nav">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold text-primary-600">MarketingOS</div>
          <div className="flex items-center space-x-6">
            <span className="text-gray-700" data-testid="user-name">Welcome, {user?.full_name}</span>
            <button
              onClick={logout}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
              data-testid="logout-btn"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8" data-testid="dashboard-content">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

        {/* Quick Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-md" data-testid="stat-campaigns">
            <div className="text-gray-600 text-sm mb-2">Active Campaigns</div>
            <div className="text-3xl font-bold text-gray-900">0</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-md" data-testid="stat-tasks">
            <div className="text-gray-600 text-sm mb-2">Open Tasks</div>
            <div className="text-3xl font-bold text-gray-900">0</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-md" data-testid="stat-health">
            <div className="text-gray-600 text-sm mb-2">Health Score</div>
            <div className="text-3xl font-bold text-green-600">--</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-md" data-testid="stat-team">
            <div className="text-gray-600 text-sm mb-2">Team Members</div>
            <div className="text-3xl font-bold text-gray-900">1</div>
          </div>
        </div>

        {/* Getting Started */}
        <div className="bg-white rounded-xl shadow-md p-8" data-testid="getting-started">
          <h2 className="text-2xl font-bold mb-6">Getting Started</h2>
          <div className="space-y-4">
            <div className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-primary-300 cursor-pointer">
              <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-primary-600 font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold">Set up your company profile</h3>
                <p className="text-gray-600 text-sm">Add your website and social media accounts</p>
              </div>
            </div>
            <div className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-primary-300 cursor-pointer">
              <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-primary-600 font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold">Invite your team</h3>
                <p className="text-gray-600 text-sm">Collaborate with your marketing team</p>
              </div>
            </div>
            <div className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-primary-300 cursor-pointer">
              <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-primary-600 font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold">Choose your subscription</h3>
                <p className="text-gray-600 text-sm">Select a plan that fits your needs</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

// Routes component that can use hooks
function AppRoutes() {
  const location = useLocation();

  // Check for session_id in URL fragment (synchronously during render to prevent race conditions)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default App;
