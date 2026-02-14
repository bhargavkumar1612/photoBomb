import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useFeatures } from '../context/FeaturesContext'
import { RefreshCw, Play, Users as UsersIcon, Image, Database, ExternalLink } from 'lucide-react'
import api from '../services/api'
import pipelineService from '../services/pipelineService'
import './AdminDashboard.css'

export default function AdminDashboard() {
    const { user } = useAuth()
    const navigate = useNavigate()
    const { animal_detection_enabled } = useFeatures()
    const [scopes, setScopes] = useState({
        faces: true,
        animals: false,
        hashtags: false
    })
    const [forceReset, setForceReset] = useState(false)
    const [loading, setLoading] = useState(false)
    const [users, setUsers] = useState([])
    const [selectedUserIds, setSelectedUserIds] = useState(new Set())
    const [jobs, setJobs] = useState([])
    const [jobsLoading, setJobsLoading] = useState(false)
    const [stats, setStats] = useState({ totalUsers: 0, totalPhotos: 0 })

    useEffect(() => {
        fetchUsers()
        fetchJobs()
    }, [])

    const fetchUsers = async () => {
        try {
            const res = await api.get('/admin/users')
            const userData = Array.isArray(res.data) ? res.data : []
            setUsers(userData)
            setStats(prev => ({ ...prev, totalUsers: userData.length }))
            // Select current user by default only if valid
            if (user && user.user_id) {
                setSelectedUserIds(new Set([user.user_id]))
            }
        } catch (err) {
            console.error('Failed to load users:', err)
        }
    }

    const fetchJobs = async () => {
        setJobsLoading(true)
        try {
            // Use new service
            const res = await pipelineService.getAdminJobs(10)
            const jobsData = Array.isArray(res.data) ? res.data : []
            setJobs(jobsData)
        } catch (err) {
            console.error('Failed to load jobs:', err)
        } finally {
            setJobsLoading(false)
        }
    }

    const toggleUser = (userId) => {
        const newSet = new Set(selectedUserIds)
        if (newSet.has(userId)) newSet.delete(userId)
        else newSet.add(userId)
        setSelectedUserIds(newSet)
    }

    const toggleAll = () => {
        if (selectedUserIds.size === users.length) setSelectedUserIds(new Set())
        else setSelectedUserIds(new Set(users.map(u => u.user_id)))
    }

    const handleRun = async () => {
        const selectedScopes = Object.keys(scopes).filter(k => scopes[k])
        if (selectedScopes.length === 0) {
            alert('Please select at least one scope')
            return
        }

        if (selectedUserIds.size === 0) {
            alert('Please select at least one user')
            return
        }

        if (forceReset && !window.confirm("⚠️ FORCE RESET WARNING\n\nThis will DELETE all existing groups/tags for the selected scopes and re-process them. This is destructive. Are you sure?")) {
            return
        }

        setLoading(true)
        try {
            // Use pipeline service (which maps to /admin/cluster or generic create)
            // Ideally backend admin/cluster maps to this.
            await pipelineService.triggerCluster({
                target_user_ids: Array.from(selectedUserIds),
                scopes: selectedScopes,
                force_reset: forceReset
            })
            alert('✅ Job queued successfully!')
            // Refresh jobs after a short delay
            setTimeout(fetchJobs, 1000)
        } catch (err) {
            alert(`❌ Error: ${err.response?.data?.detail || err.message}`)
        } finally {
            setLoading(false)
        }
    }

    const getStatusBadge = (status) => {
        const badges = {
            pending: '🕐 Pending',
            running: '⚡ Running',
            completed: '✅ Completed',
            failed: '❌ Failed'
        }
        return badges[status] || status
    }

    return (
        <div className="admin-dashboard">
            <header className="admin-header">
                <div>
                    <h1>⚡ Admin Control Center</h1>
                    <p>System maintenance and monitoring</p>
                </div>
            </header>

            {/* Stats Overview */}
            <div className="stats-grid">
                <div className="stat-card">
                    <UsersIcon size={24} />
                    <div className="stat-content">
                        <div className="stat-value">{stats?.totalUsers || 0}</div>
                        <div className="stat-label">Total Users</div>
                    </div>
                </div>
                <div className="stat-card">
                    <Database size={24} />
                    <div className="stat-content">
                        <div className="stat-value">{jobs.length}</div>
                        <div className="stat-label">Recent Jobs</div>
                    </div>
                </div>
            </div>

            <div className="admin-grid">
                {/* Job Launcher */}
                <div className="admin-card">
                    <div className="card-header">
                        <h2>🚀 Launch Maintenance Job</h2>
                        <p className="card-desc">Trigger AI clustering or re-scanning</p>
                    </div>

                    <div className="user-selector-container">
                        <div className="selector-header">
                            <label>Target Users ({selectedUserIds.size} selected)</label>
                            <button className="btn-text" onClick={toggleAll}>
                                {selectedUserIds.size === users.length ? 'Deselect All' : 'Select All'}
                            </button>
                        </div>
                        <div className="user-checklist">
                            {(users || []).map(u => (
                                <label key={u.user_id} className={`user-checkbox-row ${selectedUserIds.has(u.user_id) ? 'selected' : ''}`}>
                                    <input
                                        type="checkbox"
                                        checked={selectedUserIds.has(u.user_id)}
                                        onChange={() => toggleUser(u.user_id)}
                                    />
                                    <span className="user-info">
                                        <span className="user-name">{u.full_name} {u.is_admin ? '👑' : ''}</span>
                                        <span className="user-email">{u.email}</span>
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div className="scope-selector">
                        <label className="scope-card">
                            <input
                                type="checkbox"
                                checked={scopes.faces}
                                onChange={e => setScopes({ ...scopes, faces: e.target.checked })}
                            />
                            <div className="scope-content">
                                <strong>👤 Face Recognition</strong>
                                <span>Group unassigned faces into Persons</span>
                            </div>
                        </label>

                        {animal_detection_enabled && (
                            <label className="scope-card">
                                <input
                                    type="checkbox"
                                    checked={scopes.animals}
                                    onChange={e => setScopes({ ...scopes, animals: e.target.checked })}
                                />
                                <div className="scope-content">
                                    <strong>🐾 Animal Detection</strong>
                                    <span>Group detected animals by species</span>
                                </div>
                            </label>
                        )}

                        <label className="scope-card">
                            <input
                                type="checkbox"
                                checked={scopes.hashtags}
                                onChange={e => setScopes({ ...scopes, hashtags: e.target.checked })}
                            />
                            <div className="scope-content">
                                <strong>🏷️ Hashtags & OCR</strong>
                                <span>Retry failed/unprocessed photos</span>
                            </div>
                        </label>
                    </div>

                    <div className="danger-zone">
                        <label className="toggle-row">
                            <input
                                type="checkbox"
                                checked={forceReset}
                                onChange={e => setForceReset(e.target.checked)}
                            />
                            <span className="toggle-label">
                                <strong>⚠️ Force Full Reset</strong>
                                <span className="warning">Deletes existing groups/tags and re-scans</span>
                            </span>
                        </label>
                    </div>

                    <button
                        className="btn-primary btn-launch"
                        onClick={handleRun}
                        disabled={loading}
                    >
                        <Play size={20} />
                        {loading ? 'Launching...' : 'Launch Job'}
                    </button>
                </div>

                {/* Job History */}
                <div className="admin-card">
                    <div className="card-header">
                        <h2>📋 Job History</h2>
                        <button
                            className="btn-refresh"
                            onClick={fetchJobs}
                            disabled={jobsLoading}
                        >
                            <RefreshCw size={18} className={jobsLoading ? 'spinning' : ''} />
                            Refresh
                        </button>
                    </div>

                    <div className="jobs-table-container">
                        {(!jobs || jobs.length === 0) ? (
                            <div className="empty-state">
                                <Database size={48} />
                                <p>No jobs yet. Launch your first maintenance job!</p>
                            </div>
                        ) : (
                            <table className="jobs-table">
                                <thead>
                                    <tr>
                                        <th>Status</th>
                                        <th>Scopes</th>
                                        <th>Info</th>
                                        <th>Started</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {jobs.map(job => (
                                        <tr key={job.job_id} className={`status-${job.status}`}>
                                            <td>
                                                <span className={`status-badge status-${job.status}`}>
                                                    {getStatusBadge(job.status)}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="scope-tags">
                                                    {(job.scopes || []).map(scope => (
                                                        <span key={scope} className="scope-tag">{scope}</span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="time-cell">
                                                <div>{(job.target_user_ids || []).length} user(s)</div>
                                                <div className="message-cell" title={job.message}>{job.message || '-'}</div>
                                            </td>
                                            <td className="time-cell">
                                                {job.created_at ? new Date(job.created_at).toLocaleString() : '-'}
                                            </td>
                                            <td>
                                                <button
                                                    className="btn-icon"
                                                    title="View Details"
                                                    onClick={() => navigate(`/admin/pipelines/${job.job_id}`)}
                                                >
                                                    <ExternalLink size={16} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
