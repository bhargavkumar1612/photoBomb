import { useMemo } from 'react'
import { useSearch } from '../context/SearchContext'

export function usePhotoFilter(photos) {
    const { searchTerm, filters } = useSearch()

    const filteredPhotos = useMemo(() => {
        if (!photos) return []

        let result = [...photos]

        // 1. Search Term
        if (searchTerm) {
            const term = searchTerm.toLowerCase()
            result = result.filter(p =>
                p.filename.toLowerCase().includes(term) ||
                (p.caption && p.caption.toLowerCase().includes(term)) ||
                (p.location_name && p.location_name.toLowerCase().includes(term))
            )
        }

        // 2. File Types
        if (filters.fileTypes?.length > 0) {
            result = result.filter(p => filters.fileTypes.includes(p.mime_type))
        }

        // 3. Date Range
        if (filters.dateFrom) {
            const fromDate = new Date(filters.dateFrom)
            result = result.filter(p => new Date(p.uploaded_at || p.taken_at) >= fromDate)
        }
        if (filters.dateTo) {
            const toDate = new Date(filters.dateTo)
            toDate.setHours(23, 59, 59)
            result = result.filter(p => new Date(p.uploaded_at || p.taken_at) <= toDate)
        }

        // 4. Sorting
        switch (filters.sortBy) {
            case 'date-asc':
                result.sort((a, b) => new Date(a.uploaded_at || a.taken_at) - new Date(b.uploaded_at || b.taken_at))
                break
            case 'name':
                result.sort((a, b) => a.filename.localeCompare(b.filename))
                break
            case 'size':
                result.sort((a, b) => (b.size || 0) - (a.size || 0))
                break
            case 'date-desc':
            default:
                result.sort((a, b) => new Date(b.uploaded_at || b.taken_at) - new Date(a.uploaded_at || a.taken_at))
                break
        }

        return result
    }, [photos, searchTerm, filters])

    return filteredPhotos
}
