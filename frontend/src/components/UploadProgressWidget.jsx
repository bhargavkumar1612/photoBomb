import React, { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { backgroundTransferManager } from '../services/BackgroundTransferManager';
import { UploadCloud, CheckCircle, XCircle, Loader2, ChevronUp, ChevronDown, File } from 'lucide-react';
import './UploadProgressWidget.css';

export default function UploadProgressWidget() {
    const [transfers, setTransfers] = useState({});
    const [expanded, setExpanded] = useState(false);
    const [fileDetails, setFileDetails] = useState({}); // { [uploadId]: [{ filename, status }] }
    const queryClient = useQueryClient();
    const pollingInterval = useRef(null);

    // Initial check
    useEffect(() => {
        checkActiveTransfers();

        // Poll every 2 seconds to check status of individual files
        pollingInterval.current = setInterval(checkActiveTransfers, 2000);

        return () => {
            if (pollingInterval.current) clearInterval(pollingInterval.current);
        };
    }, []);

    const checkActiveTransfers = async () => {
        if (!('serviceWorker' in navigator) || !('BackgroundFetchManager' in self)) return;

        const registration = await navigator.serviceWorker.ready;
        const ids = await registration.backgroundFetch.getIds();

        if (ids.length === 0) {
            if (Object.keys(transfers).length > 0) {
                // All done! Clear local state and refresh storage
                setTransfers({});
                setFileDetails({});
                queryClient.invalidateQueries(['user-info']);
            }
            return;
        }

        const newTransfers = { ...transfers };
        const newFileDetails = { ...fileDetails };
        let hasChanges = false;

        for (const id of ids) {
            const bgFetch = await registration.backgroundFetch.get(id);

            // 1. Update Aggregate Progress
            if (!newTransfers[id] || newTransfers[id].downloaded !== bgFetch.downloaded) {
                newTransfers[id] = {
                    state: 'uploading',
                    downloaded: bgFetch.downloaded,
                    downloadTotal: bgFetch.downloadTotal
                };
                hasChanges = true;
            }

            // 2. Fetch records to get individual file status
            if (expanded || !newFileDetails[id]) {
                try {
                    const records = await bgFetch.matchAll();
                    const details = await Promise.all(records.map(async (record) => {
                        // Extract filename from URL query param
                        const url = new URL(record.request.url);
                        const filename = decodeURIComponent(url.searchParams.get('filename') || 'Unknown File');

                        let status = 'pending';
                        if (record.responseReady) {
                            // If response is ready, it's done (or failed, but response is there)
                            try {
                                const response = await record.responseReady;
                                status = response.ok ? 'completed' : 'error';
                            } catch {
                                status = 'error';
                            }
                        }

                        return { filename, status };
                    }));

                    // Check if details changed
                    if (JSON.stringify(newFileDetails[id]) !== JSON.stringify(details)) {
                        newFileDetails[id] = details;
                        hasChanges = true;
                    }
                } catch (e) {
                    console.error("Error fetching matchAll", e);
                }
            }
        }

        if (hasChanges) {
            setTransfers(newTransfers);
            setFileDetails(newFileDetails);
        }
    };

    // Toggle expand
    const toggleExpand = () => setExpanded(!expanded);

    const activeIds = Object.keys(transfers);
    if (activeIds.length === 0) return null;

    // Aggregate overall progress
    const totalDownloaded = activeIds.reduce((acc, id) => acc + transfers[id].downloaded, 0);
    const totalSize = activeIds.reduce((acc, id) => acc + transfers[id].downloadTotal, 0);
    const percent = totalSize > 0 ? (totalDownloaded / totalSize) * 100 : 0;

    // Cancel a specific batch upload
    const cancelBatch = async (e, id) => {
        e.stopPropagation(); // Prevent toggling expand
        if (!('serviceWorker' in navigator)) return;

        try {
            const registration = await navigator.serviceWorker.ready;
            const bgFetch = await registration.backgroundFetch.get(id);
            if (bgFetch) {
                await bgFetch.abort();
                // State will update on next poll or via event
                checkActiveTransfers();
            }
        } catch (err) {
            console.error("Failed to abort", err);
        }
    };

    return (
        <div className={`upload-widget ${expanded ? 'expanded' : ''}`}>
            {/* Header / Summary */}
            <div className="upload-header" onClick={toggleExpand}>
                <div className="header-left">
                    <div className="icon-wrapper">
                        {percent >= 100 ? <CheckCircle size={20} className="success" /> : <Loader2 size={20} className="spin" />}
                    </div>
                    <div className="header-info">
                        <span className="title">
                            {percent >= 100 ? 'Upload Completed' : `Uploading ${activeIds.length} batch(es)`}
                        </span>
                        <span className="subtitle">
                            {Math.round(percent)}% • {formatBytes(totalDownloaded)} / {formatBytes(totalSize)}
                        </span>
                    </div>
                </div>
                <div className="header-right">
                    {expanded ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                </div>
            </div>

            {/* Progress Bar (Global) */}
            <div className="progress-track">
                <div className="progress-fill" style={{ width: `${percent}%` }} />
            </div>

            {/* Detailed File List */}
            {expanded && (
                <div className="file-list">
                    {activeIds.map(id => (
                        <div key={id} className="batch-group">
                            <div className="batch-header">
                                <span>Batch {id.split('-').pop()}</span>
                                <button className="btn-cancel" onClick={(e) => cancelBatch(e, id)}>
                                    CANCEL UPLOAD
                                </button>
                            </div>
                            {fileDetails[id]?.map((file, idx) => (
                                <div key={idx} className="file-item">
                                    <File size={16} className="file-icon" />
                                    <span className="file-name" title={file.filename}>{file.filename}</span>
                                    <span className="file-status">
                                        {file.status === 'completed' && <CheckCircle size={16} className="text-green" />}
                                        {file.status === 'error' && <XCircle size={16} className="text-red" />}
                                        {file.status === 'pending' && <Loader2 size={16} className="spin text-gray" />}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
