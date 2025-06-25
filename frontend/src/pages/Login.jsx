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
import { Link } from 'react-router-dom';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Connect to backend /auth/login
    console.log(`Logging in with ${email}`);
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