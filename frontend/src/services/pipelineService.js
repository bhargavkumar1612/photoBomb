import api from './api';

const pipelineService = {
    // Get all pipelines with optional filtering
    getAll: (params) => api.get('/pipelines', { params }),

    // Get a specific pipeline details
    getOne: (id) => api.get(`/pipelines/${id}`),

    // Get tasks for a pipeline with filtering
    getTasks: (id, params) => api.get(`/pipelines/${id}/tasks`, { params }),

    // Create a new pipeline (e.g. for batch analysis)
    create: (data) => api.post('/pipelines', data),

    // Cancel a running pipeline
    cancel: (id) => api.post(`/pipelines/${id}/cancel`),

    // Rerun a pipeline (or specific failed tasks)
    rerun: (id, data) => api.post(`/pipelines/${id}/rerun`, data),

    // Delete a pipeline
    delete: (id) => api.delete(`/pipelines/${id}`),

    // Admin specific: Cluster trigger (wraps the admin endpoint if needed, or we use create)
    // The previous admin dashboard used /admin/cluster. We can keep using that or migrate.
    // Ideally, we migrate to use the generic pipeline create if it supports clustering.
    // For now, let's keep the admin hook separate or assume the frontend calls /admin/cluster directly.
    triggerCluster: (data) => api.post('/admin/cluster', data),

    // Admin specific: Get jobs (legacy support if needed, but getAll /pipelines is better)
    getAdminJobs: (limit = 20) => api.get(`/admin/jobs?limit=${limit}`)
};

export default pipelineService;
