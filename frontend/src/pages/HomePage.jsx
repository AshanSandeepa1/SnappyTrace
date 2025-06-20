import { useState } from 'react';
import { ThemeProvider, createTheme, CssBaseline, Box, Container } from '@mui/material';
import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import FeaturesSection from '../components/FeaturesSection';

const HomePage = () => {
  const [darkMode, setDarkMode] = useState(false);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: { main: '#0142d8' },
    },
  });

  const toggleDarkMode = () => setDarkMode(!darkMode);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <Box
        component="main"
        sx={{
          pt: 10,
          background: 'linear-gradient(to right, #e3f2fd, #ffffff)',
          minHeight: '100vh',
          overflowX: 'hidden',
        }}
      >
        <Container maxWidth="xl" sx={{ py: 10 }}>
          <HeroSection />
        </Container>

        <FeaturesSection />
      </Box>
    </ThemeProvider>
  );
};

export default HomePage;
