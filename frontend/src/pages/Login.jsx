import {
  Box,
  Button,
  Container,
  Divider,
  IconButton,
  InputAdornment,
  TextField,
  Typography
} from '@mui/material';
import { Visibility, VisibilityOff, Facebook, Google, Apple } from '@mui/icons-material';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';


const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const res = await api.post('/auth/login', {
        email,
        password,
      });
      const token = res.data.access_token;
      login(token);
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed';
      setError(msg);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Box display="flex" flexDirection={{ xs: 'column', md: 'row' }}>
        {/* Left Text Section */}
        <Box flex={1} pr={{ md: 6 }} mb={{ xs: 4, md: 0 }}>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Sign In to <Box component="span" color="primary.main">Secure</Box> Awesome Stuffs
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={2}>
            if you don’t have an account you can{' '}
            <Link to="/register" style={{ color: '#3f51b5', fontWeight: 500 }}><b>register here</b></Link>
          </Typography>
        </Box>

        {/* Right Form Section */}
        <Box flex={1}>
          <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />
            <Box textAlign="right">
              <Typography variant="body2" color="text.secondary">
                <Link to="#" style={{ fontSize: '0.875rem' }}>Forgot Password?</Link>
              </Typography>
            </Box>
            {error && <Typography color="error" fontSize={14}>{error}</Typography>}
            <Button type="submit" variant="contained" size="large">
              Login
            </Button>

            <Divider>Or Sign in with</Divider>
            <Box display="flex" justifyContent="center" gap={2}>
              <IconButton><Facebook /></IconButton>
              <IconButton><Apple /></IconButton>
              <IconButton><Google /></IconButton>
            </Box>
          </Box>
        </Box>
      </Box>
    </Container>
  );
};

export default Login;
