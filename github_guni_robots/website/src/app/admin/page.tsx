"use client";
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Key, 
  Database, 
  RefreshCw, 
  Plus, 
  Edit, 
  Trash2, 
  Eye, 
  EyeOff, 
  Server, 
  Download,
  Upload,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Wifi,
  WifiOff
} from 'lucide-react';

// API Key type
type ApiKey = {
  id: string;
  service_name: string;
  masked_key: string;
  is_active: boolean;
  created_at: string;
  usage_count?: number;
};

// Sync History type
type SyncHistoryEntry = {
  id: string;
  created_at: string;
  action_type: string;
  service_name: string;
  admin_user: string;
  reason: string;
};

const AdminDashboard = () => {
  // State management
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [syncHistory, setSyncHistory] = useState<SyncHistoryEntry[]>([]);
  const [piStatus, setPiStatus] = useState({ status: 'offline', last_seen: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('keys');
  
  // Database management states
  const [users, setUsers] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [userProfiles, setUserProfiles] = useState<any[]>([]);
  const [unknownUsers, setUnknownUsers] = useState<any[]>([]);
  const [databaseStats, setDatabaseStats] = useState<any>({});
  
  // Pagination state for conversations
  const [conversationsPage, setConversationsPage] = useState(0);
  const [conversationsLimit] = useState(50);
  const [conversationsTotal, setConversationsTotal] = useState(0);
  
  // Form states
  const [showAddForm, setShowAddForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [selectedKey, setSelectedKey] = useState<ApiKey | null>(null);
  const [selectedUser, setSelectedUser] = useState<any | null>(null);
  const [showUserForm, setShowUserForm] = useState(false);
  const [userFormData, setUserFormData] = useState({
    name: '',
    user_role: 'student',
    department: '',
    mobile_number: '',
    email: '',
    preferred_language: 'english'
  });
  const [formData, setFormData] = useState({
    service_name: '',
    api_key: '',
    description: '',
    expires_at: ''
  });
  
  // Sync states
  const [syncOperation, setSyncOperation] = useState('');
  const [syncStatus, setSyncStatus] = useState('');
  const [syncId, setSyncId] = useState('');

  // Database Editor State
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableRows, setTableRows] = useState<any[]>([]);
  const [editingRow, setEditingRow] = useState<any | null>(null);
  const [newRow, setNewRow] = useState<any | null>(null);

  // Remote Control Scripts (should match ALLOWED_SCRIPTS on Pi)
  const REMOTE_SCRIPTS = [
    "walk_forward.py",
    "stop.py",
    "right_hand_up.py",
    "hello.py"
  ];

  // Remote Control State
  const [remoteStatus, setRemoteStatus] = useState('');
  const [remoteLoading, setRemoteLoading] = useState(false);

  // Admin Authentication State
  const [adminApiKey, setAdminApiKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showApiKeyForm, setShowApiKeyForm] = useState(true);
  const [apiKeyInput, setApiKeyInput] = useState('');

  // API Configuration
  const API_BASE = 'https://aiec.guni.ac.in:3300'; // Main FastAPI server with all admin routes

  // API Headers
  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'x-admin-api-key': adminApiKey
  });

  // Helper function to handle 401 errors consistently
  const handle401Error = () => {
    setError('Session expired or unauthorized. Please log in again.');
    setIsAuthenticated(false);
    setShowApiKeyForm(true);
    setAdminApiKey('');
    localStorage.removeItem('admin-api-key');
  };

  // Fetch API Keys
  const fetchApiKeys = async () => {
  try {
    setLoading(true);
    setError(''); // Clear previous errors
    
    console.log('Fetching API keys from:', `${API_BASE}/admin/api-keys`);
    
    const response = await fetch(`${API_BASE}/admin/api-keys`, {
      headers: getHeaders()
    });
    
    console.log('Response status:', response.status);
    
    if (!response.ok) {
      if (response.status === 401) {
        // Handle unauthorized access
        handle401Error();
        return;
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Raw response data:', data);
    console.log('Data type:', typeof data);
    
    // Handle different response formats
    let keys = [];
    
    if (Array.isArray(data)) {
      // Direct array
      keys = data;
      console.log('Data is direct array:', keys.length, 'items');
    } else if (data && Array.isArray(data.api_keys)) {
      // Standard format: {api_keys: [...]}
      keys = data.api_keys;
      console.log('Data has api_keys array:', keys.length, 'items');
    } else if (data && Array.isArray(data.keys)) {
      // Alternative format: {keys: [...]}
      keys = data.keys;
      console.log('Data has keys array:', keys.length, 'items');
    } else if (data && typeof data === 'object') {
      // Check if there's an error in the response
      if (data.error) {
        throw new Error(`Server error: ${data.error}`);
      }
     const possibleArrays = Object.values(data).filter(v => Array.isArray(v));
      console.log('Possible arrays found:', possibleArrays.length);
      
      if (possibleArrays.length > 0) {
        // Look for array with objects that have service_name property
        const apiKeyArray = possibleArrays.find(arr => 
          arr.length > 0 && 
          typeof arr[0] === 'object' && 
          (arr[0].service_name || arr[0].name || arr[0].key_id)
        );
        
        if (apiKeyArray) {
          keys = apiKeyArray;
          console.log('Found API key array:', keys.length, 'items');
        } else {
          keys = possibleArrays[0] || [];
          console.log('Using first array found:', keys.length, 'items');
        }
      } else {
        console.log('No arrays found in response, using empty array');
        keys = [];
      }
    } else {
      console.log('Unexpected data format, using empty array');
      keys = [];
    }
    
    // Validate the keys array
    if (!Array.isArray(keys)) {
      console.error('Keys is not an array:', keys);
      keys = [];
    }
    
    console.log('Final keys array:', keys);
    setApiKeys(keys);
    
    if (keys.length === 0) {
      setError('No API keys found. The database might be empty or the table might not exist.');
    } else {
      setSuccess(`Loaded ${keys.length} API key(s) successfully`);
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);
    }
    
  } catch (err: any) {
    console.error('Error fetching API keys:', err);
    setError(`Error connecting to server: ${err.message}`);
    setApiKeys([]); // Set empty array on error
  } finally {
    setLoading(false);
  }
};

// Fetch Users
const fetchUsers = async () => {
  try {
    setLoading(true);
    const response = await fetch(`${API_BASE}/admin/users`, {
      headers: getHeaders()
    });
    const data = await response.json();
    if (response.ok) {
      setUsers(data.users || []);
      setSuccess(`Loaded ${data.users?.length || 0} users`);
    } else {
      if (response.status === 401) {
        handle401Error();
        return;
      }
      setError(data.detail || 'Failed to fetch users');
    }
  } catch (err: any) {
    setError(`Error fetching users: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// Fetch Conversations
const fetchConversations = async (page = 0) => {
  try {
    setLoading(true);
    const offset = page * conversationsLimit;
    const response = await fetch(`${API_BASE}/admin/conversations?limit=${conversationsLimit}&offset=${offset}`, {
      headers: getHeaders()
    });
    const data = await response.json();
    if (response.ok) {
      setConversations(data.conversations || []);
      setConversationsTotal(data.total || 0);
      setConversationsPage(page);
      setSuccess(`Loaded ${data.conversations?.length || 0} conversations`);
    } else {
      if (response.status === 401) {
        handle401Error();
        return;
      }
      setError(data.detail || 'Failed to fetch conversations');
    }
  } catch (err: any) {
    setError(`Error fetching conversations: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// Fetch Database Stats
const fetchDatabaseStats = async () => {
  try {
    const response = await fetch(`${API_BASE}/admin/database/stats`, {
      headers: getHeaders()
    });
    const data = await response.json();
    if (response.ok) {
      setDatabaseStats(data.stats || {});
    } else {
      if (response.status === 401) {
        handle401Error();
        return;
      }
      setError(data.detail || 'Failed to fetch database stats');
    }
  } catch (err: any) {
    setError(`Error fetching database stats: ${err.message}`);
  }
};

// Add User
const addUser = async () => {
  try {
    setLoading(true);
    const response = await fetch(`${API_BASE}/admin/users`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(userFormData)
    });
    const data = await response.json();
    if (response.ok && data.success) {
      setSuccess('User added successfully');
      setShowUserForm(false);
      setUserFormData({
        name: '',
        user_role: 'student',
        department: '',
        mobile_number: '',
        email: '',
        preferred_language: 'english'
      });
      fetchUsers();
    } else {
      setError(data.detail || 'Failed to add user');
    }
  } catch (err: any) {
    setError(`Error adding user: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// Delete User
const deleteUser = async (userId: number) => {
  if (!confirm('Are you sure you want to delete this user? This will also delete all their conversations.')) return;
  try {
    setLoading(true);
    const response = await fetch(`${API_BASE}/admin/users/${userId}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    const data = await response.json();
    if (response.ok && data.success) {
      setSuccess('User deleted successfully');
      fetchUsers();
    } else {
      setError(data.detail || 'Failed to delete user');
    }
  } catch (err: any) {
    setError(`Error deleting user: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// Delete Conversation
const deleteConversation = async (conversationId: number) => {
  if (!confirm('Are you sure you want to delete this conversation?')) return;
  try {
    setLoading(true);
    const response = await fetch(`${API_BASE}/admin/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    const data = await response.json();
    if (response.ok && data.success) {
      setSuccess('Conversation deleted successfully');
      fetchConversations(conversationsPage);
    } else {
      setError(data.detail || 'Failed to delete conversation');
    }
  } catch (err: any) {
    setError(`Error deleting conversation: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

// Add a debug function to test the database status
const debugDatabaseStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/debug/db-status`, {
      headers: getHeaders()
    });
    const data = await response.json();
    console.log('Database debug info:', data);
    alert(`Database Status:\n${JSON.stringify(data, null, 2)}`);
  } catch (err: any) {
    console.error('Error getting database status:', err);
    alert(`Error getting database status: ${err.message}`);
  }
};



  // Fetch Pi Status
  const fetchPiStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/robot/status`, {
        headers: getHeaders()
      });
      if (response.status === 401) {
        handle401Error();
        return;
      }
      const data = await response.json();
      setPiStatus(data);
    } catch (err) {
      console.error('Error fetching Pi status:', err);
    }
  };

  // Fetch Sync History
  const fetchSyncHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/sync-history`, {
        headers: getHeaders()
      });
      const data = await response.json();
      if (data.success) {
        setSyncHistory(data.sync_history);
      }
    } catch (err) {
      console.error('Error fetching sync history:', err);
    }
  };

  // Add API Key
  const addApiKey = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/api-keys`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('API key added successfully');
        setShowAddForm(false);
        setFormData({ service_name: '', api_key: '', description: '', expires_at: '' });
        fetchApiKeys();
      } else {
        setError(data.detail || 'Failed to add API key');
      }
    } catch (err) {
      setError('Error adding API key');
    } finally {
      setLoading(false);
    }
  };

  // Update API Key
  const updateApiKey = async () => {
    if (!selectedKey) return;
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/api-keys/${selectedKey.service_name}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({
          service_name: selectedKey.service_name,
          new_api_key: formData.api_key,
          reason: formData.description || 'Updated via admin dashboard'
        })
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('API key updated successfully');
        setShowEditForm(false);
        setSelectedKey(null);
        setFormData({ service_name: '', api_key: '', description: '', expires_at: '' });
        fetchApiKeys();
      } else {
        setError(data.detail || 'Failed to update API key');
      }
    } catch (err) {
      setError('Error updating API key');
    } finally {
      setLoading(false);
    }
  };

  // Deactivate API Key
  const deactivateApiKey = async (serviceName: string) => {
    if (!confirm(`Are you sure you want to deactivate the API key for ${serviceName}?`)) return;
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/api-keys/${serviceName}`, {
        method: 'DELETE',
        headers: getHeaders(),
        body: JSON.stringify({
          service_name: serviceName,
          reason: 'Deactivated via admin dashboard'
        })
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('API key deactivated successfully');
        fetchApiKeys();
      } else {
        setError(data.detail || 'Failed to deactivate API key');
      }
    } catch (err) {
      setError('Error deactivating API key');
    } finally {
      setLoading(false);
    }
  };

  // Database Sync Operations (example: sync to Pi)
  const syncDatabase = async (operation: string) => {
    try {
      setLoading(true);
      setSyncOperation(operation);
      setSyncStatus('initiating');
      let command, db_url;
      if (operation === 'sync_from_server') {
        // You must provide a public URL to the latest DB file
        db_url = 'https://your-server.com/path/to/voice_assistant_enhanced.db';
        command = 'update_db';
      } else {
        setError('Only sync_from_server (update_db) is implemented in this demo');
        setLoading(false);
        return;
      }
      // Send MQTT command via FastAPI
      const response = await fetch(`${API_BASE}/admin/robot/send-command`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ command, db_url })
      });
      const data = await response.json();
      if (data.command_id) {
        setSyncId(data.command_id);
        setSyncStatus('waiting');
        setSuccess('Database sync initiated');
        pollSyncStatus(data.command_id);
      } else {
        setError(data.detail || 'Failed to initiate sync');
        setSyncStatus('failed');
      }
    } catch (err) {
      setError('Error initiating sync');
      setSyncStatus('failed');
    } finally {
      setLoading(false);
    }
  };

  // Poll Sync Status (wait for MQTT response)
  const pollSyncStatus = async (syncId: string) => {
    const maxAttempts = 30;
    let attempts = 0;
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/admin/robot/command-response/${syncId}`, {
          headers: getHeaders()
        });
        const data = await response.json();
        if (data.status === 'pending' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000);
        } else if (data.status === 'success') {
          setSyncStatus('completed');
          setSuccess('Database sync completed successfully');
        } else if (data.status === 'error' || data.status === 'unauthorized' || data.status === 'invalid') {
          setSyncStatus('failed');
          setError(data.error || 'Sync failed');
        } else {
          setSyncStatus('failed');
          setError(data.message || 'Sync failed or timed out');
        }
      } catch (err) {
        setSyncStatus('failed');
        setError('Error checking sync status');
      }
    };
    poll();
  };

  // Export Database
  const exportDatabase = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/export-database`, {
        headers: getHeaders()
      });
      const data = await response.json();
      
      if (data.success) {
        // Download as JSON file
        const blob = new Blob([JSON.stringify(data.database_data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `database_export_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        setSuccess('Database exported successfully');
      } else {
        setError('Failed to export database');
      }
    } catch (err) {
      setError('Error exporting database');
    } finally {
      setLoading(false);
    }
  };

  // Fetch tables from Pi
  const fetchTables = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/pi/tables`, { headers: getHeaders() });
      const data = await response.json();
      if (data.status === 'success') setTables(data.tables);
      else setError(data.error || 'Failed to fetch tables');
    } catch (err) {
      setError('Error fetching tables');
    } finally {
      setLoading(false);
    }
  };

  // Fetch table data
  const fetchTableRows = async (table: string) => {
    try {
      setLoading(true);
      setSelectedTable(table);
      setEditingRow(null);
      setNewRow(null);
      const response = await fetch(`${API_BASE}/admin/pi/table/${table}`, { headers: getHeaders() });
      const data = await response.json();
      if (data.status === 'success') setTableRows(data.rows);
      else setError(data.error || 'Failed to fetch table data');
    } catch (err) {
      setError('Error fetching table data');
    } finally {
      setLoading(false);
    }
  };

  // Update row
  const updateRow = async (row: any) => {
    try {
      setLoading(true);
      const id = row.id;
      const { id: _, ...rowData } = row;
      const response = await fetch(`${API_BASE}/admin/pi/table/${selectedTable}/row/${id}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(rowData)
      });
      const data = await response.json();
      if (data.status === 'success') {
        setSuccess('Row updated');
        fetchTableRows(selectedTable!);
        setEditingRow(null);
      } else setError(data.error || 'Failed to update row');
    } catch (err) {
      setError('Error updating row');
    } finally {
      setLoading(false);
    }
  };

  // Insert row
  const insertRow = async (row: any) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/pi/table/${selectedTable}/row`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(row)
      });
      const data = await response.json();
      if (data.status === 'success') {
        setSuccess('Row inserted');
        fetchTableRows(selectedTable!);
        setNewRow(null);
      } else setError(data.error || 'Failed to insert row');
    } catch (err) {
      setError('Error inserting row');
    } finally {
      setLoading(false);
    }
  };

  // Delete row
  const deleteRow = async (row: any) => {
    if (!window.confirm('Delete this row?')) return;
    try {
      setLoading(true);
      const id = row.id;
      const response = await fetch(`${API_BASE}/admin/pi/table/${selectedTable}/row/${id}`, {
        method: 'DELETE',
        headers: getHeaders()
      });
      const data = await response.json();
      if (data.status === 'success') {
        setSuccess('Row deleted');
        fetchTableRows(selectedTable!);
      } else setError(data.error || 'Failed to delete row');
    } catch (err) {
      setError('Error deleting row');
    } finally {
      setLoading(false);
    }
  };

  // Send remote control command
  const sendRemoteCommand = async (script: string) => {
    setRemoteLoading(true);
    setRemoteStatus('');
    try {
      const response = await fetch(`${API_BASE}/admin/robot/send-command`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ command: `python3 ${script}` })
      });
      const data = await response.json();
      if (data.command_id) {
        // Poll for result
        let attempts = 0;
        const poll = async () => {
          const resp = await fetch(`${API_BASE}/admin/robot/command-response/${data.command_id}`, {
            headers: getHeaders()
          });
          const result = await resp.json();
          if (result.status === 'pending' && attempts < 20) {
            attempts++;
            setTimeout(poll, 1000);
          } else if (result.status === 'success') {
            setRemoteStatus(result.output || 'Success');
          } else {
            setRemoteStatus(result.error || result.message || 'Failed');
          }
          setRemoteLoading(false);
        };
        poll();
      } else {
        setRemoteStatus(data.detail || 'Failed to send command');
        setRemoteLoading(false);
      }
    } catch (err) {
      setRemoteStatus('Error sending command');
      setRemoteLoading(false);
    }
  };

  // Admin Authentication Functions
  const authenticateAdmin = async () => {
    if (!apiKeyInput.trim()) {
      setError('Please enter an API key');
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      // Test the API key by making a simple request
      const response = await fetch(`${API_BASE}/admin/api-keys`, {
        headers: {
          'Content-Type': 'application/json',
          'x-admin-api-key': apiKeyInput.trim()
        }
      });
      
      if (response.ok) {
        setAdminApiKey(apiKeyInput.trim());
        setIsAuthenticated(true);
        setShowApiKeyForm(false);
        setApiKeyInput('');
        setSuccess('Successfully authenticated as admin');
        
        // Store in localStorage for session persistence
        localStorage.setItem('admin-api-key', apiKeyInput.trim());
      } else {
        setError('Invalid admin API key. Please check your credentials.');
      }
    } catch (err: any) {
      setError(`Authentication failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const logoutAdmin = () => {
    setAdminApiKey('');
    setIsAuthenticated(false);
    setShowApiKeyForm(true);
    setApiKeyInput('');
    localStorage.removeItem('admin-api-key');
    setSuccess('Logged out successfully');
  };

  const changeApiKey = () => {
    setShowApiKeyForm(true);
    setApiKeyInput('');
  };

  // Check for stored API key on component mount
  useEffect(() => {
    const storedKey = localStorage.getItem('admin-api-key');
    if (storedKey) {
      setAdminApiKey(storedKey);
      setIsAuthenticated(true);
      setShowApiKeyForm(false);
    }
  }, []);

  // Initialize data only when authenticated
  useEffect(() => {
    if (isAuthenticated && adminApiKey) {
      fetchApiKeys();
      fetchPiStatus();
      fetchSyncHistory();
      fetchUsers();
      fetchConversations();
      fetchDatabaseStats();
    }
  }, [isAuthenticated, adminApiKey]);

  // Set up periodic Pi status check when authenticated
  useEffect(() => {
    if (isAuthenticated && adminApiKey) {
      const interval = setInterval(fetchPiStatus, 30000); // Every 30 seconds
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, adminApiKey]);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError('');
        setSuccess('');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Admin API Key Authentication Form */}
      {showApiKeyForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Admin Authentication</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Admin API Key</label>
                  <input
                    type="password"
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && authenticateAdmin()}
                    className="w-full p-2 border rounded-lg"
                    placeholder="Enter your admin API key"
                    autoFocus
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={authenticateAdmin}
                    disabled={loading || !apiKeyInput.trim()}
                    className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  >
                    {loading ? 'Authenticating...' : 'Authenticate'}
                  </button>
                </div>
                <p className="text-sm text-gray-600">
                  Enter your admin API key to access the dashboard.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
            <p className="text-gray-600">Manage API keys and database synchronization</p>
          </div>
          {isAuthenticated && (
            <div className="flex items-center gap-4">
              <button
                onClick={changeApiKey}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                Change API Key
              </button>
              <button
                onClick={logoutAdmin}
                className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Dashboard Content - Only show when authenticated */}
      {isAuthenticated && (
        <>
          {/* Pi Status */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {piStatus.status === 'online' ? (
                  <Wifi className="w-5 h-5 text-green-500" />
                ) : (
                  <WifiOff className="w-5 h-5 text-red-500" />
                )}
                Raspberry Pi Status
              </CardTitle>
            </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              piStatus.status === 'online' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {piStatus.status === 'online' ? 'Online' : 'Offline'}
            </span>
            {piStatus.last_seen && (
              <span className="text-sm text-gray-500">
                Last seen: {new Date(piStatus.last_seen * 1000).toLocaleString()}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Alerts */}
      {error && (
        <Alert className="mb-4 border-red-200 bg-red-50">
          <XCircle className="w-4 h-4 text-red-500" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-4 border-green-200 bg-green-50">
          <CheckCircle className="w-4 h-4 text-green-500" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Admin API Key Form */}
      {showApiKeyForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Admin Authentication</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">API Key</label>
                  <input
                    type="password"
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className="w-full p-2 border rounded-lg"
                    placeholder="Enter admin API key"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={authenticateAdmin}
                    disabled={loading}
                    className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  >
                    {loading ? 'Authenticating...' : 'Login as Admin'}
                  </button>
                  <button
                    onClick={logoutAdmin}
                    className="flex-1 bg-gray-500 text-white py-2 rounded-lg hover:bg-gray-600"
                  >
                    Logout
                  </button>
                </div>
                <div className="text-sm text-gray-500">
                  Note: This API key is different from the user API keys. It provides access to admin features.
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setActiveTab('keys')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'keys'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Key className="w-4 h-4 inline mr-2" />
          API Keys
        </button>
        <button
          onClick={() => { setActiveTab('users'); fetchUsers(); }}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'users'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Eye className="w-4 h-4 inline mr-2" />
          Users
        </button>
        <button
          onClick={() => { setActiveTab('conversations'); fetchConversations(0); }}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'conversations'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Database className="w-4 h-4 inline mr-2" />
          Conversations
        </button>
        <button
          onClick={() => { setActiveTab('database'); fetchDatabaseStats(); }}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'database'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Server className="w-4 h-4 inline mr-2" />
          Database
        </button>
        <button
          onClick={() => setActiveTab('sync')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'sync'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <RefreshCw className="w-4 h-4 inline mr-2" />
          Sync
        </button>
        <button
          onClick={() => { setActiveTab('db'); fetchTables(); }}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'db'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Database className="w-4 h-4 inline mr-2" />
          Pi Editor
        </button>
        <button
          onClick={() => setActiveTab('remote')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'remote'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Server className="w-4 h-4 inline mr-2" />
          Remote Control
        </button>
      </div>

      {/* API Keys Tab */}
      {activeTab === 'keys' && (
        <div>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>API Key Management</CardTitle>
                <button
                  onClick={() => setShowAddForm(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  <Plus className="w-4 h-4" />
                  Add New Key
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">Loading...</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Service</th>
                        <th className="text-left py-2">Key</th>
                        <th className="text-left py-2">Status</th>
                        <th className="text-left py-2">Created</th>
                        <th className="text-left py-2">Usage</th>
                        <th className="text-left py-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {apiKeys.map((key) => (
                        <tr key={key.id} className="border-b">
                          <td className="py-3 font-medium">{key.service_name}</td>
                          <td className="py-3 font-mono text-sm">{key.masked_key}</td>
                          <td className="py-3">
                            <span className={`px-2 py-1 rounded-full text-xs ${
                              key.is_active 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {key.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="py-3 text-sm text-gray-600">
                            {new Date(key.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3">{key.usage_count || 0}</td>
                          <td className="py-3">
                            <div className="flex gap-2">
                              <button
                                onClick={() => {
                                  setSelectedKey(key);
                                  setFormData({ service_name: key.service_name, api_key: '', description: '', expires_at: '' });
                                  setShowEditForm(true);
                                }}
                                className="p-1 text-blue-500 hover:bg-blue-50 rounded"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => deactivateApiKey(key.service_name)}
                                className="p-1 text-red-500 hover:bg-red-50 rounded"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Add API Key Form */}
          {showAddForm && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Add New API Key</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Service Name</label>
                      <select
                        value={formData.service_name}
                        onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
                        className="w-full p-2 border rounded-lg"
                      >
                        <option value="">Select Service</option>
                        <option value="groq">Groq</option>
                        <option value="elevenlabs">ElevenLabs</option>
                        <option value="compreface">CompreFace</option>
                        <option value="openai">OpenAI</option>
                        <option value="gemini">Gemini</option>
                        <option value="anthropic">Anthropic</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">API Key</label>
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter API key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Description (Optional)</label>
                      <input
                        type="text"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Description"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={addApiKey}
                        disabled={loading}
                        className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                      >
                        Add Key
                      </button>
                      <button
                        onClick={() => setShowAddForm(false)}
                        className="flex-1 bg-gray-500 text-white py-2 rounded-lg hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Edit API Key Form */}
          {showEditForm && selectedKey && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Update API Key - {selectedKey.service_name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">New API Key</label>
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter new API key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Reason for Update</label>
                      <input
                        type="text"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Reason for update"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={updateApiKey}
                        disabled={loading}
                        className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                      >
                        Update Key
                      </button>
                      <button
                        onClick={() => setShowEditForm(false)}
                        className="flex-1 bg-gray-500 text-white py-2 rounded-lg hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>User Management</CardTitle>
                <button
                  onClick={() => setShowUserForm(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  <Plus className="w-4 h-4" />
                  Add New User
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">Loading...</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Name</th>
                        <th className="text-left py-2">Role</th>
                        <th className="text-left py-2">Department</th>
                        <th className="text-left py-2">Mobile</th>
                        <th className="text-left py-2">Language</th>
                        <th className="text-left py-2">Created</th>
                        <th className="text-left py-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id} className="border-b">
                          <td className="py-3 font-medium">{user.name}</td>
                          <td className="py-3">{user.user_role}</td>
                          <td className="py-3">{user.department || 'N/A'}</td>
                          <td className="py-3">{user.mobile_number || 'N/A'}</td>
                          <td className="py-3">{user.preferred_language}</td>
                          <td className="py-3">{new Date(user.created_at).toLocaleDateString()}</td>
                          <td className="py-3">
                            <div className="flex gap-2">
                              <button
                                onClick={() => deleteUser(user.id)}
                                className="p-1 text-red-500 hover:bg-red-50 rounded"
                                title="Delete user"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {users.length === 0 && (
                    <div className="text-center py-8 text-gray-500">No users found</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Add User Form */}
          {showUserForm && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
              <Card className="w-full max-w-md">
                <CardHeader>
                  <CardTitle>Add New User</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Name</label>
                      <input
                        type="text"
                        value={userFormData.name}
                        onChange={(e) => setUserFormData({...userFormData, name: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter user name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Role</label>
                      <select
                        value={userFormData.user_role}
                        onChange={(e) => setUserFormData({...userFormData, user_role: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                      >
                        <option value="student">Student</option>
                        <option value="faculty">Faculty</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Department</label>
                      <input
                        type="text"
                        value={userFormData.department}
                        onChange={(e) => setUserFormData({...userFormData, department: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter department"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Mobile Number</label>
                      <input
                        type="text"
                        value={userFormData.mobile_number}
                        onChange={(e) => setUserFormData({...userFormData, mobile_number: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter mobile number"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Email</label>
                      <input
                        type="email"
                        value={userFormData.email}
                        onChange={(e) => setUserFormData({...userFormData, email: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                        placeholder="Enter email"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Preferred Language</label>
                      <select
                        value={userFormData.preferred_language}
                        onChange={(e) => setUserFormData({...userFormData, preferred_language: e.target.value})}
                        className="w-full p-2 border rounded-lg"
                      >
                        <option value="english">English</option>
                        <option value="hindi">Hindi</option>
                        <option value="gujarati">Gujarati</option>
                      </select>
                    </div>
                    <div className="flex gap-2 pt-4">
                      <button
                        onClick={addUser}
                        disabled={loading}
                        className="flex-1 bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                      >
                        {loading ? 'Adding...' : 'Add User'}
                      </button>
                      <button
                        onClick={() => setShowUserForm(false)}
                        className="flex-1 bg-gray-500 text-white py-2 px-4 rounded-lg hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Conversations Tab */}
      {activeTab === 'conversations' && (
        <div>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Conversation History</CardTitle>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">
                    Showing {conversationsPage * conversationsLimit + 1}-{Math.min((conversationsPage + 1) * conversationsLimit, conversationsTotal)} of {conversationsTotal}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => fetchConversations(conversationsPage - 1)}
                      disabled={conversationsPage === 0}
                      className="px-3 py-1 bg-gray-200 rounded disabled:opacity-50"
                    >
                      ←
                    </button>
                    <button
                      onClick={() => fetchConversations(conversationsPage + 1)}
                      disabled={(conversationsPage + 1) * conversationsLimit >= conversationsTotal}
                      className="px-3 py-1 bg-gray-200 rounded disabled:opacity-50"
                    >
                      →
                    </button>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">Loading...</div>
              ) : (
                <div className="space-y-4">
                  {conversations.map((conv) => (
                    <div key={conv.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{conv.user_name}</span>
                          <span className="text-sm text-gray-500">{conv.language_used}</span>
                          <span className="text-sm text-gray-500">
                            {new Date(conv.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <button
                          onClick={() => deleteConversation(conv.id)}
                          className="p-1 text-red-500 hover:bg-red-50 rounded"
                          title="Delete conversation"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="space-y-2">
                        <div>
                          <span className="text-sm font-medium text-blue-600">User:</span>
                          <p className="text-sm mt-1 pl-4 border-l-2 border-blue-200">{conv.user_input}</p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-green-600">AI:</span>
                          <p className="text-sm mt-1 pl-4 border-l-2 border-green-200">{conv.ai_response}</p>
                        </div>
                        {conv.summary && (
                          <div>
                            <span className="text-sm font-medium text-gray-600">Summary:</span>
                            <p className="text-sm mt-1 pl-4 border-l-2 border-gray-200">{conv.summary}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {conversations.length === 0 && (
                    <div className="text-center py-8 text-gray-500">No conversations found</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Database Stats Tab */}
      {activeTab === 'database' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Database Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{databaseStats.users_count || 0}</div>
                  <div className="text-sm text-gray-600">Total Users</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{databaseStats.conversations_count || 0}</div>
                  <div className="text-sm text-gray-600">Total Conversations</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">{databaseStats.conversations_last_7_days || 0}</div>
                  <div className="text-sm text-gray-600">Conversations (7 days)</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{databaseStats.new_users_last_30_days || 0}</div>
                  <div className="text-sm text-gray-600">New Users (30 days)</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{databaseStats.api_keys_count || 0}</div>
                  <div className="text-sm text-gray-600">API Keys</div>
                </div>
                <div className="bg-indigo-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-indigo-600">{databaseStats.unknown_users_count || 0}</div>
                  <div className="text-sm text-gray-600">Unknown Users</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-gray-600">
                    {databaseStats.database_size_bytes ? Math.round(databaseStats.database_size_bytes / 1024 / 1024 * 100) / 100 : 0} MB
                  </div>
                  <div className="text-sm text-gray-600">Database Size</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Database Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <button
                  onClick={() => fetchDatabaseStats()}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  <RefreshCw className="w-4 h-4" />
                  Refresh Stats
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Database Sync Tab */}
      {activeTab === 'sync' && (
        <div className="space-y-6">
          {/* Sync Operations */}
          <Card>
            <CardHeader>
              <CardTitle>Database Synchronization</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <button
                  onClick={() => syncDatabase('sync_from_server')}
                  disabled={loading || piStatus.status !== 'online'}
                  className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <Upload className="w-8 h-8 mb-2 text-blue-500" />
                  <span className="font-medium">Sync to Pi</span>
                  <span className="text-sm text-gray-500 text-center">Send server data to Pi</span>
                </button>
                
                <button
                  onClick={() => syncDatabase('sync_to_server')}
                  disabled={loading || piStatus.status !== 'online'}
                  className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <Download className="w-8 h-8 mb-2 text-green-500" />
                  <span className="font-medium">Sync from Pi</span>
                  <span className="text-sm text-gray-500 text-center">Get Pi data to server</span>
                </button>
                
                <button
                  onClick={() => syncDatabase('full_backup')}
                  disabled={loading || piStatus.status !== 'online'}
                  className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <Server className="w-8 h-8 mb-2 text-purple-500" />
                  <span className="font-medium">Full Backup</span>
                  <span className="text-sm text-gray-500 text-center">Complete Pi backup</span>
                </button>
                
                <button
                  onClick={exportDatabase}
                  disabled={loading}
                  className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <Download className="w-8 h-8 mb-2 text-orange-500" />
                  <span className="font-medium">Export Server</span>
                  <span className="text-sm text-gray-500 text-center">Export server database</span>
                </button>
              </div>
              
              {/* Sync Status */}
              {syncStatus && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    {syncStatus === 'initiating' && <AlertCircle className="w-5 h-5 text-yellow-500 animate-pulse" />}
                    {syncStatus === 'waiting' && <Clock className="w-5 h-5 text-blue-500 animate-pulse" />}
                    {syncStatus === 'completed' && <CheckCircle className="w-5 h-5 text-green-500" />}
                    {syncStatus === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                    <span className="font-medium">
                      Sync Status: {syncStatus} {syncOperation && `(${syncOperation})`}
                    </span>
                  </div>
                  {syncId && (
                    <div className="text-sm text-gray-600 mt-1">
                      Sync ID: {syncId}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sync History */}
          <Card>
            <CardHeader>
              <CardTitle>Sync History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Date</th>
                      <th className="text-left py-2">Operation</th>
                      <th className="text-left py-2">Service</th>
                      <th className="text-left py-2">Admin User</th>
                      <th className="text-left py-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncHistory.map((entry) => (
                      <tr key={entry.id} className="border-b">
                        <td className="py-3 text-sm">
                          {new Date(entry.created_at).toLocaleString()}
                        </td>
                        <td className="py-3">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            entry.action_type.includes('sync') 
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {entry.action_type}
                          </span>
                        </td>
                        <td className="py-3">{entry.service_name}</td>
                        <td className="py-3">{entry.admin_user}</td>
                        <td className="py-3 text-sm text-gray-600">{entry.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Database Editor Tab */}
      {activeTab === 'db' && (
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Pi Database Tables</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 mb-4">
                <select
                  value={selectedTable || ''}
                  onChange={e => fetchTableRows(e.target.value)}
                  className="p-2 border rounded"
                >
                  <option value="">Select Table</option>
                  {tables.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {selectedTable && (
                  <button onClick={() => setNewRow({})} className="bg-green-500 text-white px-3 py-1 rounded">Add Row</button>
                )}
              </div>
              {selectedTable && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        {tableRows[0] && Object.keys(tableRows[0]).map(col => <th key={col} className="text-left py-2">{col}</th>)}
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tableRows.map((row, idx) => (
                        editingRow && editingRow.id === row.id ? (
                          <tr key={row.id}>
                            {Object.keys(row).map(col => (
                              <td key={col}>
                                <input
                                  value={editingRow[col] ?? ''}
                                  onChange={e => setEditingRow({ ...editingRow, [col]: e.target.value })}
                                  className="p-1 border rounded"
                                />
                              </td>
                            ))}
                            <td>
                              <button onClick={() => updateRow(editingRow)} className="text-green-600 mr-2">Save</button>
                              <button onClick={() => setEditingRow(null)} className="text-gray-600">Cancel</button>
                            </td>
                          </tr>
                        ) : (
                          <tr key={row.id}>
                            {Object.keys(row).map(col => <td key={col}>{row[col]}</td>)}
                            <td>
                              <button onClick={() => setEditingRow(row)} className="text-blue-600 mr-2">Edit</button>
                              <button onClick={() => deleteRow(row)} className="text-red-600">Delete</button>
                            </td>
                          </tr>
                        )
                      ))}
                      {newRow && (
                        <tr>
                          {tableRows[0] && Object.keys(tableRows[0]).map(col => (
                            <td key={col}>
                              <input
                                value={newRow[col] ?? ''}
                                onChange={e => setNewRow({ ...newRow, [col]: e.target.value })}
                                className="p-1 border rounded"
                              />
                            </td>
                          ))}
                          <td>
                            <button onClick={() => insertRow(newRow)} className="text-green-600 mr-2">Insert</button>
                            <button onClick={() => setNewRow(null)} className="text-gray-600">Cancel</button>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Remote Control Tab */}
      {activeTab === 'remote' && (
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Remote Control (Raspberry Pi)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 mb-4">
                {REMOTE_SCRIPTS.map(script => (
                  <button
                    key={script}
                    onClick={() => sendRemoteCommand(script)}
                    disabled={remoteLoading || piStatus.status !== 'online'}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {script.replace('.py', '').replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
              {remoteLoading && <div className="text-blue-600">Sending command...</div>}
              {remoteStatus && <div className="mt-2 text-gray-800">Result: {remoteStatus}</div>}
            </CardContent>
          </Card>
        </div>
      )}
        </>
      )}

      {/* Alerts - Always show */}
      {error && (
        <Alert className="mb-4 border-red-200 bg-red-50">
          <XCircle className="w-4 h-4 text-red-500" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-4 border-green-200 bg-green-50">
          <CheckCircle className="w-4 h-4 text-green-500" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default AdminDashboard;