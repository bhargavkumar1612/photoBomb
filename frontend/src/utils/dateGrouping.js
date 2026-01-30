export const groupPhotosByDate = (photos, options = {}) => {
    if (!photos || photos.length === 0) return [];

    const { dateField = null } = options;

    // Day/Relative grouping (default)
    const groups = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    // ... logic ...

    photos.forEach(photo => {
        let dateVal = null;
        if (dateField && photo[dateField]) {
            dateVal = photo[dateField];
        } else {
            dateVal = photo.taken_at || photo.uploaded_at;
        }

        const date = new Date(dateVal);
        const dateStr = date.toDateString(); // "Fri Jan 11 2026"

        let label = '';
        if (dateStr === today.toDateString()) {
            label = 'Today';
        } else if (dateStr === yesterday.toDateString()) {
            label = 'Yesterday';
        } else {
            // "January 14, 2025"
            label = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        }

        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    const priorityLabels = ['Today', 'Yesterday', 'This Week', 'This Month'];
    const groupList = Object.keys(groups).map(label => ({ label, photos: groups[label] }));

    groupList.sort((a, b) => {
        const idxA = priorityLabels.indexOf(a.label);
        const idxB = priorityLabels.indexOf(b.label);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;

        // Parse date from long string format or use first photo's date
        const getPhotoDate = (p) => {
            if (dateField && p[dateField]) return new Date(p[dateField]);
            return new Date(p.taken_at || p.uploaded_at);
        };

        const dateA = getPhotoDate(a.photos[0]);
        const dateB = getPhotoDate(b.photos[0]);
        return dateB - dateA;
    });

    return groupList;
};

export const groupPhotosByMonth = (photos) => {
    if (!photos || photos.length === 0) return [];

    const groups = {};
    photos.forEach(photo => {
        const date = new Date(photo.taken_at || photo.uploaded_at);
        const label = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    return Object.keys(groups)
        .map(label => ({ label, photos: groups[label] }))
        .sort((a, b) => new Date(b.label) - new Date(a.label));
};

export const groupPhotosByYear = (photos) => {
    if (!photos || photos.length === 0) return [];

    const groups = {};
    photos.forEach(photo => {
        const date = new Date(photo.taken_at || photo.uploaded_at);
        const label = date.getFullYear().toString();
        if (!groups[label]) groups[label] = [];
        groups[label].push(photo);
    });

    return Object.keys(groups)
        .map(label => ({ label, photos: groups[label] }))
        .sort((a, b) => parseInt(b.label) - parseInt(a.label));
};
