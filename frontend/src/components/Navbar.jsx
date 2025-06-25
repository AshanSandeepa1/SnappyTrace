import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  Button,
  Drawer,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { Link } from 'react-router-dom';
import { useThemeContext } from '../store/ThemeContext';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import { useState, useEffect } from 'react';

const pages = [
  { label: 'Home', path: '/' },
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Upload', path: '/upload' },
  { label: 'Verify', path: '/verify' },
  { label: 'Settings', path: '/settings' },
  { label: 'Login', path: '/login' },
  { label: 'Register', path: '/register' },
];

const Navbar = () => {
  const { mode, toggle } = useThemeContext();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <AppBar
      position="sticky"
      elevation={scrolled ? 3 : 0}
      sx={{
        backdropFilter: scrolled ? 'blur(6px)' : 'none',
        backgroundColor: scrolled
          ? mode === 'light'
            ? 'rgba(255,255,255,0.8)'
            : 'rgba(0,0,0,0.6)'
          : 'transparent',
        transition: 'background-color 0.3s, backdrop-filter 0.3s',
        color: mode === 'light' ? 'black' : 'white', // Fix for text/icon color
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton edge="start" onClick={() => setOpen(true)} sx={{ mr: 1, display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <Typography
            component={Link}
            to="/"
            sx={{
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <img src="/logo.svg" alt="SnappyTrace" style={{ height: 32 }} />
            <Typography
              variant="h6"
              sx={{
                color: mode === 'light' ? '#1976d2' : '#fff', // blue in light, white in dark
                fontWeight: 'bold',
              }}
            >
              SnappyTrace
            </Typography>
          </Typography>

        </Box>
        <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 2 }}>
          {pages.map((p) => (
            <Button key={p.path} component={Link} to={p.path} sx={{ color: 'inherit' }}>
              {p.label}
            </Button>
          ))}
          <IconButton onClick={toggle} sx={{ ml: 1, color: 'inherit' }}>
            {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
        </Box>
        <IconButton onClick={toggle} sx={{ ml: 1, display: { md: 'none' }, color: 'inherit' }}>
          {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
        </IconButton>
      </Toolbar>
      <Drawer anchor="left" open={open} onClose={() => setOpen(false)} sx={{ display: { md: 'none' } }}>
        <Box sx={{ width: 200 }} role="presentation" onClick={() => setOpen(false)}>
          <List>
            {pages.map((p) => (
              <ListItem button key={p.path} component={Link} to={p.path}>
                <ListItemText primary={p.label} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </AppBar>
  );
};

export default Navbar;
