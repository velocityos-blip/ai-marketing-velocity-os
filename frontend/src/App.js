import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { SubscriptionPage, AIToolsPage, TasksPage } from './pages';
import { Home, Account, Desk } from './Experience';
import './App.css';
import WorkspaceShell from './WorkspaceShell';

const basePath = process.env.PUBLIC_URL || '';
const API_URL = process.env.REACT_APP_BACKEND_URL || basePath;

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
        window.history.replaceState(null, '', basePath + '/dashboard');
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
function LandingPage() { return <Home user={useAuth().user}/>; }
function LoginPage() { return <Account mode="login" auth={useAuth()} basePath={basePath}/>; }
function RegisterPage() { return <Account mode="register" auth={useAuth()} basePath={basePath}/>; }
function DashboardPage() { return <Desk auth={useAuth()} api={api}/>; }

function TeamPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadTeamData();
  }, [user]);

  const loadTeamData = async () => {
    if (!user?.workspace_id) return;
    
    try {
      const [membersRes, invitesRes] = await Promise.all([
        api.get(`/api/workspaces/${user.workspace_id}/members`),
        api.get('/api/invitations')
      ]);
      setMembers(membersRes.data);
      setInvitations(invitesRes.data);
    } catch (error) {
      console.error('Error loading team data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setInviteLoading(true);

    try {
      await api.post('/api/invitations', {
        email: inviteEmail,
        workspace_id: user.workspace_id,
        role: inviteRole
      });
      setSuccess('Invitation sent successfully!');
      setInviteEmail('');
      setInviteRole('member');
      setShowInviteModal(false);
      loadTeamData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send invitation');
    } finally {
      setInviteLoading(false);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Are you sure you want to remove this member?')) return;

    try {
      await api.delete(`/api/workspaces/${user.workspace_id}/members/${memberId}`);
      setSuccess('Member removed successfully');
      loadTeamData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove member');
    }
  };

  const handleAcceptInvitation = async (invitationId) => {
    try {
      await api.post(`/api/invitations/${invitationId}/accept`);
      setSuccess('Invitation accepted!');
      loadTeamData();
      window.location.reload(); // Refresh to update workspace
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to accept invitation');
    }
  };

  const handleDeclineInvitation = async (invitationId) => {
    try {
      await api.post(`/api/invitations/${invitationId}/decline`);
      setSuccess('Invitation declined');
      loadTeamData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to decline invitation');
    }
  };

  const canInvite = user?.role === 'owner' || user?.role === 'admin';
  const canRemove = user?.role === 'owner' || user?.role === 'admin';

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold text-primary-600">MarketingOS</div>
            <div className="flex space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 text-gray-700 hover:text-primary-600 font-medium"
              >
                Dashboard
              </button>
              <button
                onClick={() => navigate('/team')}
                className="px-4 py-2 text-primary-600 font-medium border-b-2 border-primary-600"
              >
                Team
              </button>
            </div>
          </div>
          <div className="flex items-center space-x-6">
            <span className="text-gray-700">Welcome, {user?.full_name}</span>
            <button onClick={logout} className="px-4 py-2 text-gray-600 hover:text-gray-800">
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8" data-testid="team-page">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Team Members</h1>
            <p className="text-gray-600 mt-2">Manage your workspace team</p>
          </div>
          {canInvite && (
            <button
              onClick={() => setShowInviteModal(true)}
              className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
              data-testid="invite-member-btn"
            >
              + Invite Member
            </button>
          )}
        </div>

        {/* Alerts */}
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-4" data-testid="error-message">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 text-green-600 p-4 rounded-lg mb-4" data-testid="success-message">
            {success}
          </div>
        )}

        {/* Pending Invitations for current user */}
        {invitations.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Pending Invitations</h2>
            {invitations.map((invite) => (
              <div key={invite.invitation_id} className="bg-white p-4 rounded-lg mb-3 flex justify-between items-center">
                <div>
                  <p className="font-semibold">{invite.workspace_name}</p>
                  <p className="text-sm text-gray-600">Invited by {invite.invited_by_name} as {invite.role}</p>
                </div>
                <div className="space-x-3">
                  <button
                    onClick={() => handleAcceptInvitation(invite.invitation_id)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    data-testid="accept-invitation-btn"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => handleDeclineInvitation(invite.invitation_id)}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                    data-testid="decline-invitation-btn"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Team Members List */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Member</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Email</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Role</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Joined</th>
                  {canRemove && <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {members.map((member) => (
                  <tr key={member.member_id} data-testid="team-member-row">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 font-semibold">
                          {member.user?.full_name?.charAt(0)}
                        </div>
                        <span className="ml-3 font-medium">{member.user?.full_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600">{member.user?.email}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        member.role === 'owner' ? 'bg-purple-100 text-purple-700' :
                        member.role === 'admin' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {member.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {new Date(member.joined_at).toLocaleDateString()}
                    </td>
                    {canRemove && (
                      <td className="px-6 py-4">
                        {member.role !== 'owner' && member.user_id !== user.user_id && (
                          <button
                            onClick={() => handleRemoveMember(member.member_id)}
                            className="text-red-600 hover:text-red-800 font-medium"
                            data-testid="remove-member-btn"
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" data-testid="invite-modal">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-6">Invite Team Member</h2>
            
            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                  placeholder="colleague@example.com"
                  required
                  data-testid="invite-email-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                  data-testid="invite-role-select"
                >
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="flex space-x-3 mt-6">
                <button
                  type="submit"
                  disabled={inviteLoading}
                  className="flex-1 bg-primary-600 text-white py-3 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
                  data-testid="send-invitation-btn"
                >
                  {inviteLoading ? 'Sending...' : 'Send Invitation'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 bg-gray-200 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-300"
                  data-testid="cancel-invitation-btn"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router basename={basePath || "/"}>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

// Routes component that can use hooks
function AppRoutes() {
  const location = useLocation();
  const { user, logout } = useAuth();

  // Check for session_id in URL fragment (synchronously during render to prevent race conditions)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  const shell = user && ["/dashboard","/team","/tasks","/subscription","/ai-tools"].includes(location.pathname);
  const Wrapper = shell ? WorkspaceShell : React.Fragment;
  return (
    <Wrapper {...(shell ? {user,logout} : {})}><div className={["/team","/tasks","/subscription","/ai-tools"].includes(location.pathname)?"vos-tools-theme":undefined}><Routes>
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
      <Route
        path="/team"
        element={
          <ProtectedRoute>
            <TeamPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/subscription"
        element={
          <ProtectedRoute>
            <SubscriptionPage user={user} onLogout={logout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ai-tools"
        element={
          <ProtectedRoute>
            <AIToolsPage user={user} onLogout={logout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tasks"
        element={
          <ProtectedRoute>
            <TasksPage user={user} onLogout={logout} />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes></div></Wrapper>
  );
}

export default App;
