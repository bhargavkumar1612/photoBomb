import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Clock, AlertTriangle, CheckCircle, RefreshCw, XCircle, Play } from 'lucide-react'
import pipelineService from '../services/pipelineService'
import './PipelineDetail.css'

export default function PipelineDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [pipeline, setPipeline] = useState(null)
    const [tasks, setTasks] = useState([])
    const [loading, setLoading] = useState(true)
    const [tasksLoading, setTasksLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('all') // 'all', 'failed', 'completed'

    useEffect(() => {
        fetchPipeline()
        fetchTasks()

        // Poll for updates if running
        const interval = setInterval(() => {
            if (pipeline && ['running', 'queued', 'pending'].includes(pipeline.status)) {
                fetchPipeline(false)
                fetchTasks(false)
            }
        }, 3000)

        return () => clearInterval(interval)
    }, [id, pipeline?.status])

    const fetchPipeline = async (showLoading = true) => {
        if (showLoading) setLoading(true)
        try {
            const res = await pipelineService.getOne(id)
            setPipeline(res.data)
        } catch (err) {
            console.error("Failed to fetch pipeline", err)
        } finally {
            if (showLoading) setLoading(false)
        }
    }

    const fetchTasks = async (showLoading = true) => {
        if (showLoading) setTasksLoading(true)
        try {
            // Fetch tasks based on active filter? For now fetch all (up to limit)
            // Ideally we paginate or filter on backend
            const res = await pipelineService.getTasks(id, { limit: 100 })
            setTasks(res.data)
        } catch (err) {
            console.error("Failed to fetch tasks", err)
        } finally {
            if (showLoading) setTasksLoading(false)
        }
    }

    const handleCancel = async () => {
        if (!window.confirm("Are you sure you want to cancel this pipeline?")) return;
        try {
            await pipelineService.cancel(id)
            fetchPipeline()
        } catch (err) {
            alert("Failed to cancel pipeline")
        }
    }

    const handleRerun = async () => {
        try {
            await pipelineService.rerun(id, { task_filter: 'failed' })
            fetchPipeline()
        } catch (err) {
            alert("Failed to start rerun")
        }
    }

    if (loading && !pipeline) return <div className="loading-screen">Loading Pipeline...</div>
    if (!pipeline) return <div className="error-screen">Pipeline not found</div>

    const progress = pipeline.progress || { percentage: 0, completed: 0, total: 0 }
    const filteredTasks = tasks.filter(t => {
        if (activeTab === 'failed') return t.status === 'failed'
        if (activeTab === 'completed') return t.status === 'completed'
        return true
    })

    return (
        <div className="pipeline-detail-page">
            <header className="detail-header">
                <button className="btn-back" onClick={() => navigate('/admin')}>
                    <ArrowLeft size={20} /> Back
                </button>
                <div className="header-content">
                    <div>
                        <div className="pipeline-meta">
                            <span className={`status-badge status-${pipeline.status}`}>
                                {pipeline.status.toUpperCase()}
                            </span>
                            <span className="pipeline-id">ID: {id.slice(0, 8)}...</span>
                        </div>
                        <h1>{pipeline.name || `Pipeline ${id.slice(0, 8)}`}</h1>
                    </div>
                    <div className="header-actions">
                        {['running', 'queued'].includes(pipeline.status) && (
                            <button className="btn-danger" onClick={handleCancel}>
                                <XCircle size={18} /> Cancel
                            </button>
                        )}
                        {(pipeline.status === 'failed' || pipeline.status === 'completed') && (
                            <button className="btn-primary" onClick={handleRerun}>
                                <RefreshCw size={18} /> Rerun Failed
                            </button>
                        )}
                    </div>
                </div>
            </header>

            {/* Progress Section */}
            <section className="progress-section">
                <div className="progress-bar-container">
                    <div
                        className={`progress-fill status-${pipeline.status}`}
                        style={{ width: `${progress.percentage}%` }}
                    />
                </div>
                <div className="progress-stats">
                    <div className="stat-item">
                        <span className="stat-label">Progress</span>
                        <span className="stat-value">{progress.percentage.toFixed(1)}%</span>
                        <span className="stat-sub">{progress.completed} / {progress.total} items</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Running Time</span>
                        <span className="stat-value">
                            {pipeline.duration_ms ? `${(pipeline.duration_ms / 1000).toFixed(1)}s` : '-'}
                        </span>
                    </div>
                    {pipeline.performance && (
                        <div className="stat-item">
                            <span className="stat-label">Avg. Time/Item</span>
                            <span className="stat-value">
                                {pipeline.performance.avg_processing_time_ms ? `${pipeline.performance.avg_processing_time_ms}ms` : '-'}
                            </span>
                        </div>
                    )}
                </div>
            </section>

            {/* Config & Metrics */}
            <div className="metrics-grid">
                <div className="metric-card">
                    <h3>Configuration</h3>
                    <div className="config-tags">
                        {pipeline.config?.scopes?.map(s => (
                            <span key={s} className="scope-tag">{s}</span>
                        ))}
                    </div>
                    <p className="config-desc">{pipeline.description}</p>
                </div>
                {pipeline.performance && (
                    <div className="metric-card">
                        <h3>Detailed Metrics</h3>
                        <div className="metrics-list">
                            <div className="metric-row">
                                <span>Face Detection</span>
                                <strong>{pipeline.performance.avg_face_detection_ms || '-'}ms</strong>
                            </div>
                            <div className="metric-row">
                                <span>OCR</span>
                                <strong>{pipeline.performance.avg_ocr_ms || '-'}ms</strong>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Task List */}
            <section className="tasks-section">
                <div className="tasks-header">
                    <h2>Task Log</h2>
                    <div className="tabs">
                        <button
                            className={`tab ${activeTab === 'all' ? 'active' : ''}`}
                            onClick={() => setActiveTab('all')}
                        >All</button>
                        <button
                            className={`tab ${activeTab === 'failed' ? 'active' : ''}`}
                            onClick={() => setActiveTab('failed')}
                        >Failed ({pipeline.progress?.failed || 0})</button>
                        <button
                            className={`tab ${activeTab === 'completed' ? 'active' : ''}`}
                            onClick={() => setActiveTab('completed')}
                        >Completed</button>
                    </div>
                </div>

                <div className="tasks-table-container">
                    <table className="tasks-table">
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>File</th>
                                <th>Duration</th>
                                <th>Info</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredTasks.length === 0 ? (
                                <tr><td colSpan="4" className="empty-cell">No tasks found</td></tr>
                            ) : (
                                filteredTasks.map(task => (
                                    <tr key={task.task_id} className={`row-${task.status}`}>
                                        <td>
                                            <span className={`status-dot status-${task.status}`} title={task.status} />
                                            {task.status}
                                        </td>
                                        <td>{task.photo_filename}</td>
                                        <td>{task.total_time_ms ? `${task.total_time_ms}ms` : '-'}</td>
                                        <td className="info-cell">
                                            {task.error_message ? (
                                                <span className="error-text" title={task.error_message}>
                                                    <AlertTriangle size={14} /> {task.error_message}
                                                </span>
                                            ) : (
                                                <span className="success-text">
                                                    {task.faces_detected > 0 && `👤 ${task.faces_detected} `}
                                                    {task.text_words_extracted > 0 && `📝 `}
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}
