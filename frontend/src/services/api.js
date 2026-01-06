// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000', // or Docker hostname in production
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
