// src/components/Navbar.jsx
import { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Stack,
  IconButton,
  Box,
  Container,
  useScrollTrigger,
  Slide,
  useTheme,
} from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import Logo from '../assets/logo.png';

const Navbar = ({ darkMode, toggleDarkMode }) => {
  const [elevate, setElevate] = useState(false);
  const theme = useTheme();

  // Scroll listener to add blur and elevation
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setElevate(true);
      } else {
        setElevate(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <AppBar
      position="fixed"
      elevation={elevate ? 4 : 0}
      sx={{
        backdropFilter: elevate ? 'blur(10px)' : 'none',
        backgroundColor: elevate
          ? theme.palette.mode === 'light'
            ? 'rgba(255, 255, 255, 0.8)'
            : 'rgba(0, 0, 0, 0.6)'
          : 'transparent',
        transition: 'background-color 0.3s ease, backdrop-filter 0.3s ease',
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ justifyContent: 'space-between' }}>
          <Box
            sx={{
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
            }}
            >
            <Box
                component="img"
                src={Logo}
                alt="SnappyTrace Logo"
                sx={{ height: 40, mr: 1 }}  // margin-right for spacing
            />
            <Typography variant="h6" fontWeight="bold" color="primary">
                SnappyTrace
            </Typography>
            </Box>
          <Stack direction="row" spacing={2} alignItems="center">
            <Button color="primary">About Us</Button>
            <Button color="primary">Pricing</Button>
            <Button color="primary">Login</Button>
            <Button variant="contained" color="primary">
              Get Started
            </Button>
            <IconButton onClick={toggleDarkMode} color="black">
              {darkMode ? <Brightness7 /> : <Brightness4 />}
            </IconButton>
          </Stack>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navbar;
