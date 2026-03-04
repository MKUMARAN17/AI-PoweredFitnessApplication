import axios from 'axios';

const API_BASE_URL = 'http://localhost:8090'; // Gateway URL

const api = axios.create({
    baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authService = {
    login: (credentials) => api.post('/api/users/login', credentials),
    register: (userData) => api.post('/api/users/register', userData),
};

export const activityService = {
    getActivities: (userId) => api.get('/api/activities', {
        headers: { 'X-User-ID': userId }
    }),
    addActivity: (activityData) => api.post('/api/activities', activityData),
};

export const aiService = {
    getSuggestions: (data) => api.post('/api/recommendations/process', data),
};

export default api;
