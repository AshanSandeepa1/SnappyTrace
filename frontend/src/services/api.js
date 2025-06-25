// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000', // or Docker hostname in production
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
