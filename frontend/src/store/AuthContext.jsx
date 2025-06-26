import { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from "jwt-decode";
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const navigate = useNavigate();

  // Load user from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      try {
        const decoded = jwt_decode(savedToken);
        setUser(decoded);
        setToken(savedToken);
      } catch {
        logout();
      }
    }
  }, []);

  const login = (newToken) => {
    try {
      const decoded = jwt_decode(newToken);
      localStorage.setItem('token', newToken);
      setUser(decoded);
      setToken(newToken);
    } catch (err) {
      console.error('Failed to decode token:', err);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setToken(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
