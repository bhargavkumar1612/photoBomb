import { useEffect } from 'react'

/**
 * Hook to handle common modal keyboard interactions.
 * - Closes on Escape
 * - Optionally triggers confirm on Enter (ctrl+enter or just enter depending on needs)
 * 
 * @param {Object} options
 * @param {boolean} options.isOpen - Whether the modal is open
 * @param {Function} options.onClose - Function to call on Escape
 * @param {Function} [options.onConfirm] - Function to call on Enter
 * @param {boolean} [options.confirmOnEnter] - Whether to trigger onConfirm on Enter key (default: false, to avoid accidental submits in textareas etc unless handled)
 */
export function useModalKeyboard({ isOpen, onClose, onConfirm, confirmOnEnter = false }) {
    useEffect(() => {
        if (!isOpen) return

        const handleKeyDown = (e) => {
            // Escape to close
            if (e.key === 'Escape') {
                e.preventDefault()
                onClose()
            }

            // Enter to confirm (if enabled)
            // We check !e.shiftKey to allow multiline text if strictly needed, but for modals usually Enter is OK.
            // We also check if default wasn't prevented by a focused input/button handling it.
            else if (confirmOnEnter && e.key === 'Enter' && onConfirm) {
                // If focus is on a button or link, let standard behavior happen (clicking it)
                // If focus is on an input, form submit usually handles it.
                // This is mostly for when focus is on body or non-input elements
                const tagName = document.activeElement?.tagName
                if (tagName !== 'BUTTON' && tagName !== 'A' && tagName !== 'TEXTAREA') {
                    // Check if inside a form, let form handle it? 
                    // But if we want to enforce it:
                    e.preventDefault()
                    onConfirm()
                }
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isOpen, onClose, onConfirm, confirmOnEnter])
}
