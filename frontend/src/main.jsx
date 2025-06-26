import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { AuthProvider } from './store/AuthContext';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
   
        <App />
    
  </React.StrictMode>
);
