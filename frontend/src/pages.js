// Additional page components for Marketing SaaS
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Helper function for API calls
const apiCall = async (endpoint, options = {}) => {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

// Subscription/Billing Page
export function SubscriptionPage({ user, onLogout }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [subscription, setSubscription] = useState(null);

  const packages = [
    { id: 'starter', name: 'Starter', price: 19, color: 'blue' },
    { id: 'professional', name: 'Professional', price: 49, color: 'purple' },
    { id: 'agency', name: 'Agency', price: 99, color: 'green' },
  ];

  const handleSubscribe = async (packageId) => {
    setLoading(true);
    try {
      const response = await apiCall('/api/payments/checkout', {
        method: 'POST',
        body: JSON.stringify({
          package_id: packageId,
          user_count: 5,
          origin_url: window.location.origin,
        }),
      });
      window.location.href = response.url;
    } catch (error) {
      alert('Failed to create checkout session');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold text-primary-600">MarketingOS</div>
            <button onClick={() => navigate('/dashboard')} className="px-4 py-2 text-gray-700 hover:text-primary-600">Dashboard</button>
            <button onClick={() => navigate('/subscription')} className="px-4 py-2 text-primary-600 border-b-2 border-primary-600">Subscription</button>
          </div>
          <button onClick={onLogout} className="px-4 py-2 text-gray-600 hover:text-gray-800">Logout</button>
        </div>
      </nav>

      <div className="container mx-auto px-6 py-8">
        <h1 className="text-3xl font-bold mb-8">Choose Your Plan</h1>
        <div className="grid md:grid-cols-3 gap-8">
          {packages.map((pkg) => (
            <div key={pkg.id} className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-bold mb-4">{pkg.name}</h2>
              <div className="text-4xl font-bold text-primary-600 mb-4">${pkg.price}<span className="text-lg">/month</span></div>
              <p className="text-gray-600 mb-6">Up to 5 users included</p>
              <button
                onClick={() => handleSubscribe(pkg.id)}
                disabled={loading}
                className={`w-full py-3 bg-${pkg.color}-600 text-white rounded-lg hover:bg-${pkg.color}-700 disabled:opacity-50`}
              >
                {loading ? 'Processing...' : 'Subscribe'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// AI Tools Page
export function AIToolsPage({ user, onLogout }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('copywriter');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  
  // Copywriter form
  const [copyForm, setCopyForm] = useState({
    content_type: 'blog',
    topic: '',
    tone: 'professional',
    length: 'medium',
  });

  const handleCopywriter = async () => {
    if (!copyForm.topic) return alert('Please enter a topic');
    setLoading(true);
    try {
      const response = await apiCall('/api/ai/copywriter', {
        method: 'POST',
        body: JSON.stringify(copyForm),
      });
      setResult(response.content);
    } catch (error) {
      alert('Failed to generate content');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold text-primary-600">MarketingOS</div>
            <button onClick={() => navigate('/dashboard')} className="px-4 py-2 text-gray-700">Dashboard</button>
            <button onClick={() => navigate('/ai-tools')} className="px-4 py-2 text-primary-600 border-b-2 border-primary-600">AI Tools</button>
          </div>
          <button onClick={onLogout} className="px-4 py-2 text-gray-600 hover:text-gray-800">Logout</button>
        </div>
      </nav>

      <div className="container mx-auto px-6 py-8">
        <h1 className="text-3xl font-bold mb-8">AI Marketing Tools</h1>

        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="mb-6">
            <div className="flex space-x-4 border-b">
              <button
                onClick={() => setActiveTab('copywriter')}
                className={`px-4 py-2 ${activeTab === 'copywriter' ? 'border-b-2 border-primary-600 text-primary-600' : 'text-gray-600'}`}
              >
                Copywriter
              </button>
              <button
                onClick={() => setActiveTab('assessment')}
                className={`px-4 py-2 ${activeTab === 'assessment' ? 'border-b-2 border-primary-600 text-primary-600' : 'text-gray-600'}`}
              >
                Health Assessment
              </button>
            </div>
          </div>

          {activeTab === 'copywriter' && (
            <div>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Content Type</label>
                  <select
                    value={copyForm.content_type}
                    onChange={(e) => setCopyForm({ ...copyForm, content_type: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg"
                  >
                    <option value="blog">Blog Post</option>
                    <option value="social_media">Social Media</option>
                    <option value="email">Email</option>
                    <option value="ad_copy">Ad Copy</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Tone</label>
                  <select
                    value={copyForm.tone}
                    onChange={(e) => setCopyForm({ ...copyForm, tone: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg"
                  >
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="friendly">Friendly</option>
                    <option value="formal">Formal</option>
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Topic</label>
                <input
                  type="text"
                  value={copyForm.topic}
                  onChange={(e) => setCopyForm({ ...copyForm, topic: e.target.value })}
                  placeholder="Enter your topic..."
                  className="w-full px-4 py-2 border rounded-lg"
                />
              </div>
              <button
                onClick={handleCopywriter}
                disabled={loading}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Content'}
              </button>
            </div>
          )}

          {result && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-bold mb-2">Generated Content:</h3>
              <p className="whitespace-pre-wrap">{result}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Tasks Page (Kanban Board)
export function TasksPage({ user, onLogout }) {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium',
    status: 'todo',
  });

  useEffect(() => {
    loadTasks();
  }, [user]);

  const loadTasks = async () => {
    if (!user?.workspace_id) return;
    try {
      const data = await apiCall(`/api/tasks/workspace/${user.workspace_id}`);
      setTasks(data);
    } catch (error) {
      console.error('Failed to load tasks');
    }
  };

  const handleCreateTask = async () => {
    if (!newTask.title) return alert('Task title is required');
    try {
      await apiCall('/api/tasks', {
        method: 'POST',
        body: JSON.stringify(newTask),
      });
      setShowModal(false);
      setNewTask({ title: '', description: '', priority: 'medium', status: 'todo' });
      loadTasks();
    } catch (error) {
      alert('Failed to create task');
    }
  };

  const tasksByStatus = {
    todo: tasks.filter(t => t.status === 'todo'),
    in_progress: tasks.filter(t => t.status === 'in_progress'),
    completed: tasks.filter(t => t.status === 'completed'),
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold text-primary-600">MarketingOS</div>
            <button onClick={() => navigate('/dashboard')} className="px-4 py-2 text-gray-700">Dashboard</button>
            <button onClick={() => navigate('/tasks')} className="px-4 py-2 text-primary-600 border-b-2 border-primary-600">Tasks</button>
          </div>
          <div className="flex items-center space-x-4">
            <button onClick={() => setShowModal(true)} className="px-4 py-2 bg-primary-600 text-white rounded-lg">+ New Task</button>
            <button onClick={onLogout} className="px-4 py-2 text-gray-600">Logout</button>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-6 py-8">
        <h1 className="text-3xl font-bold mb-8">Task Board</h1>
        <div className="grid md:grid-cols-3 gap-6">
          {Object.entries({ todo: 'To Do', in_progress: 'In Progress', completed: 'Completed' }).map(([status, title]) => (
            <div key={status} className="bg-gray-100 rounded-lg p-4">
              <h2 className="font-bold text-lg mb-4">{title} ({tasksByStatus[status].length})</h2>
              <div className="space-y-3">
                {tasksByStatus[status].map((task) => (
                  <div key={task.task_id} className="bg-white p-4 rounded-lg shadow">
                    <h3 className="font-semibold">{task.title}</h3>
                    {task.description && <p className="text-sm text-gray-600 mt-1">{task.description}</p>}
                    <div className="flex items-center justify-between mt-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        task.priority === 'high' ? 'bg-red-100 text-red-700' :
                        task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {task.priority}
                      </span>
                      {task.assignee && <span className="text-xs text-gray-500">{task.assignee.full_name}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 max-w-md w-full">
            <h2 className="text-2xl font-bold mb-4">Create Task</h2>
            <div className="space-y-4">
              <input
                type="text"
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="Task title"
                className="w-full px-4 py-2 border rounded-lg"
              />
              <textarea
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                placeholder="Description"
                className="w-full px-4 py-2 border rounded-lg"
                rows={3}
              />
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg"
              >
                <option value="low">Low Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="high">High Priority</option>
              </select>
              <div className="flex space-x-3">
                <button onClick={handleCreateTask} className="flex-1 bg-primary-600 text-white py-2 rounded-lg">Create</button>
                <button onClick={() => setShowModal(false)} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
