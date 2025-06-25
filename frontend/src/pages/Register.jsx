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

const Register = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState('');

  const handleChange = (field) => (e) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    if (field === 'password') checkStrength(value);
  };

  const checkStrength = (password) => {
    const strongRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\d\s:])([\S]{8,})$/;
    if (strongRegex.test(password)) setPasswordStrength('Strong');
    else if (password.length >= 6) setPasswordStrength('Medium');
    else setPasswordStrength('Weak');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      const res = await api.post('/auth/register', {
        name: form.name,
        email: form.email,
        password: form.password,
      });

      const token = res.data.access_token;
      localStorage.setItem('token', token);
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed';
      setError(msg);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Box display="flex" flexDirection={{ xs: 'column', md: 'row' }}>
        {/* Left Text Section */}
        <Box flex={1} pr={{ md: 6 }} mb={{ xs: 4, md: 0 }}>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Sign up to <Box component="span" color="primary.main">Secure</Box> Awesome Stuffs
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={2}>
            if you already have an account you can{' '}
            <Link to="/login" style={{ color: '#3f51b5', fontWeight: 500 }}><b>login here</b></Link>
          </Typography>
        </Box>

        {/* Form Section */}
        <Box flex={1}>
          <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Full Name"
              value={form.name}
              onChange={handleChange('name')}
              required
              fullWidth
            />
            <TextField
              label="Email"
              type="email"
              value={form.email}
              onChange={handleChange('email')}
              required
              fullWidth
            />
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={form.password}
              onChange={handleChange('password')}
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
              helperText={`Password strength: ${passwordStrength}`}
            />
            <TextField
              label="Confirm Password"
              type={showConfirm ? 'text' : 'password'}
              value={form.confirmPassword}
              onChange={handleChange('confirmPassword')}
              required
              fullWidth
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowConfirm(!showConfirm)} edge="end">
                      {showConfirm ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />
            {error && <Typography color="error" fontSize={14}>{error}</Typography>}
            <Button type="submit" variant="contained" size="large">
              Sign up
            </Button>

            <Divider>Or Sign up with</Divider>
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

export default Register;
