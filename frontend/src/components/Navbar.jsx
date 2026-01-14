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
  Menu,
  MenuItem,
  Avatar,
  Tooltip,
  Divider
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { Link, useNavigate } from 'react-router-dom';
import { useThemeContext } from '../store/ThemeContext';
import { Brightness4, Brightness7, AccountCircle } from '@mui/icons-material';
import { useState, useEffect } from 'react';
import { useAuth } from '../store/AuthContext';

const Navbar = () => {
  const { mode, toggle } = useThemeContext();
  const { isAuthenticated, user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();

  const handleMenuOpen = (event) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const pages = [
    { label: 'Home', path: '/' },
    ...(isAuthenticated ? [
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Upload', path: '/upload' }
    ] : []),
    { label: 'Verify', path: '/verify' },
    { label: 'About', path: '/about' },
    { label: 'Contact', path: '/contact' },
  ];

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
        color: mode === 'light' ? 'black' : 'white',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        {/* Left section: logo */}
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
              sx={{ color: mode === 'light' ? '#1976d2' : '#fff', fontWeight: 'bold' }}
            >
              SnappyTrace
            </Typography>
          </Typography>
        </Box>

        {/* Right-aligned nav links */}
        <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 2, alignItems: 'center', ml: 'auto' }}>
          {pages.map((p) => (
            <Button key={p.path} component={Link} to={p.path} sx={{ color: 'inherit' }}>
              {p.label}
            </Button>
          ))}
        </Box>

        {/* Right: profile and theme */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title="Account">
            <IconButton onClick={handleMenuOpen} color="inherit" sx={{ p: 0.5, ml: 2 }}>
              <AccountCircle sx={{ fontSize: 28 }} />
            </IconButton>
          </Tooltip>
          <IconButton onClick={toggle} sx={{ color: 'inherit' }}>
            {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
        </Box>

        {/* Profile Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          PaperProps={{
            sx: {
              width: 250,
              p: 2,
              borderRadius: 2,
              mt: 1.5,
            }
          }}
        >
          {isAuthenticated ? ([
            <Typography key="email" variant="subtitle2" sx={{ px: 1.5, pb: 1 }}>{user?.email}</Typography>,
            <Divider key="divider" sx={{ mb: 1 }} />,
            <MenuItem key="dashboard" onClick={() => { navigate('/dashboard'); handleMenuClose(); }}>Dashboard</MenuItem>,
            <MenuItem key="upload" onClick={() => { navigate('/upload'); handleMenuClose(); }}>Upload</MenuItem>,
            <MenuItem key="settings" onClick={() => { navigate('/settings'); handleMenuClose(); }}>Settings</MenuItem>,
            <MenuItem key="logout" onClick={() => { logout(); handleMenuClose(); }}>Logout</MenuItem>
          ]) : ([
            <Button
              key="login"
              fullWidth
              variant="contained"
              onClick={() => {
                navigate('/login');
                handleMenuClose();
              }}
              sx={{ mb: 1 }}
            >Sign In</Button>,
            <Button
              key="register"
              fullWidth
              variant="outlined"
              onClick={() => {
                navigate('/register');
                handleMenuClose();
              }}
            >Register</Button>
          ])}
        </Menu>
      </Toolbar>

      {/* Drawer for mobile nav */}
      <Drawer anchor="left" open={open} onClose={() => setOpen(false)} sx={{ display: { md: 'none' } }}>
        <Box sx={{ width: 200 }} role="presentation" onClick={() => setOpen(false)}>
          <List>
            {pages.map((p) => (
              <ListItem button key={p.path} component={Link} to={p.path}>
                <ListItemText primary={p.label} />
              </ListItem>
            ))}
            {!isAuthenticated && ([
              <ListItem button key="login" component={Link} to="/login">
                <ListItemText primary="Login" />
              </ListItem>,
              <ListItem button key="register" component={Link} to="/register">
                <ListItemText primary="Register" />
              </ListItem>
            ])}
            {isAuthenticated && ([
              <ListItem button key="settings" component={Link} to="/settings">
                <ListItemText primary="Settings" />
              </ListItem>,
              <ListItem button key="logout" onClick={logout}>
                <ListItemText primary="Logout" />
              </ListItem>
            ])}
          </List>
        </Box>
      </Drawer>
    </AppBar>
  );
};

export default Navbar;
