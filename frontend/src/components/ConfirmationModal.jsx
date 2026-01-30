import { X, AlertTriangle } from 'lucide-react'
import { useModalKeyboard } from '../hooks/useModalKeyboard'
import './ConfirmationModal.css'

export default function ConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    title = "Confirm Action",
    message = "Are you sure you want to proceed?",
    confirmText = "Confirm",
    cancelText = "Cancel",
    isDestructive = false,
    confirmLoading = false
}) {
    useModalKeyboard({ isOpen, onClose, onConfirm, confirmOnEnter: true })

    if (!isOpen) return null

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content confirmation-modal" onClick={e => e.stopPropagation()}>
                <div className="confirmation-header">
                    <div className={`icon-badge ${isDestructive ? 'destructive' : 'primary'}`}>
                        <AlertTriangle size={24} />
                    </div>
                </div>

                <div className="confirmation-body">
                    <h3>{title}</h3>
                    <p>{message}</p>
                </div>

                <div className="confirmation-actions">
                    <button
                        className="btn-secondary"
                        onClick={onClose}
                        disabled={confirmLoading}
                    >
                        {cancelText}
                    </button>
                    <button
                        className={`btn-primary ${isDestructive ? 'btn-danger' : ''}`}
                        onClick={onConfirm}
                        disabled={confirmLoading}
                    >
                        {confirmLoading ? 'Processing...' : confirmText}
                    </button>
                </div>
            </div>
        </div>
    )
}
