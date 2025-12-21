import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { backgroundTransferManager } from '../services/BackgroundTransferManager'
import api from '../services/api'
import './Upload.css'

export default function Upload() {
    const [selectedFiles, setSelectedFiles] = useState([])
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState({})
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const handleFileSelect = (e) => {
        const files = Array.from(e.target.files)
        setSelectedFiles(files)
    }

    const handleUpload = async () => {
        if (selectedFiles.length === 0) return

        setUploading(true)

        try {
            await backgroundTransferManager.uploadFiles(selectedFiles)

            // Navigate back immediately - upload continues in background
            setTimeout(() => navigate('/'), 500)
        } catch (error) {
            console.error('Upload initiation failed:', error)
            alert('Failed to start background upload. Please try again.')
            setUploading(false)
        }
    }

    return (
        <div className="upload-container">
            <header className="upload-header">
                <h1>Upload Photos</h1>
                <button onClick={() => navigate('/')} className="btn-secondary">
                    Back to Timeline
                </button>
            </header>

            <main className="upload-content">
                <div className="upload-zone">
                    <input
                        type="file"
                        id="file-input"
                        multiple
                        accept="image/*"
                        onChange={handleFileSelect}
                        style={{ display: 'none' }}
                    />
                    <label htmlFor="file-input" className="upload-label">
                        <div className="upload-icon">📸</div>
                        <p>Click to select photos</p>
                        <small>or drag and drop</small>
                    </label>
                </div>

                {selectedFiles.length > 0 && (
                    <div className="selected-files">
                        <h3>Selected Files ({selectedFiles.length})</h3>
                        <ul>
                            {selectedFiles.map((file, index) => (
                                <li key={index}>
                                    <span>{file.name}</span>
                                    {progress[file.name] !== undefined && (
                                        <div className="progress-bar">
                                            <div
                                                className="progress-fill"
                                                style={{ width: `${Math.max(0, progress[file.name])}%` }}
                                            />
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                        <button
                            onClick={handleUpload}
                            disabled={uploading}
                            className="btn-primary"
                        >
                            {uploading ? 'Uploading...' : 'Upload All'}
                        </button>
                    </div>
                )}
            </main>
        </div>
    )
}
