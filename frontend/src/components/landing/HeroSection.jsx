import { Box, Button, Container, Typography, useTheme, Stack } from '@mui/material';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import FadeInSection from '../common/FadeInSection';

const HeroSection = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box
      sx={{
        pt: { xs: 8, md: 12 },
        pb: { xs: 6, md: 10 },
        background: isDark
          ? 'linear-gradient(to right, #0f2027, #203a43, #2c5364)'
          : 'linear-gradient(to right, #e3f2fd, #f5faff)',
        textAlign: 'center',
      }}
    >
      <Container maxWidth="md">
        <FadeInSection>
          <Stack direction="row" justifyContent="center" alignItems="center" spacing={1} sx={{ mb: 2 }}>
            <img src="/logo.svg" alt="SnappyTrace" style={{ height: 48 }} />
            <Typography
              variant="h4"
              sx={{ fontWeight: 'bold', color: isDark ? '#fff' : '#1976d2' }}
            >
              SnappyTrace
            </Typography>
          </Stack>

          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            AI-Powered Digital Ownership & Tamper Protection
          </Typography>
          <Typography variant="h6" sx={{ color: 'text.secondary', mb: 4 }}>
            Our mission is to safeguard your media with invisible, AI-driven watermarks. Advanced security, copyright protection, and tamper detection make us your trusted partner in digital ownership.
          </Typography>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center">
            <motion.div whileHover={{ scale: 1.05 }}>
              <Button variant="contained" color="primary" size="large" component={Link} to="/register">
                Get Started
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }}>
              <Button variant="outlined" size="large" component={Link} to="/login">
                Log In
              </Button>
            </motion.div>
          </Stack>
        </FadeInSection>
      </Container>
    </Box>
  );
};

export default HeroSection;
