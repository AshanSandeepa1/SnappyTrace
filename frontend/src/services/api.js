import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const uploadFile = async (file) => {
  // placeholder: would send to backend
  return api.post('/upload', file);
};

export const verifyFile = async (id) => {
  // placeholder: would check verification
  return api.get(`/verify/${id}`);
};

export default api;
