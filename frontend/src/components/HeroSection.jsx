import { Box, Grid, Typography, Stack, Button } from '@mui/material';
import HeroImage from '../assets/hero-placeholder.jpg';

const HeroSection = () => (
  <Grid container spacing={6} alignItems="center" justifyContent="center">
    <Grid item xs={12} md={6}>
      <Typography variant="h3" fontWeight="bold" gutterBottom>
        Protecting Your Digital Content.
      </Typography>
      <Typography variant="h6" color="text.secondary" paragraph>
        Our mission is to safeguard your media with invisible, AI-driven watermarks. Advanced security,
        copyright protection, and tamper detection make us your trusted partner in digital ownership.
      </Typography>
      <Stack direction="row" spacing={2} mt={4}>
        <Button variant="contained" size="large" color="primary">
          Get Started
        </Button>
        <Button variant="outlined" size="large">
          Learn More
        </Button>
      </Stack>
    </Grid>
    <Grid item xs={12} md={6}>
      <Box
        component="img"
        src={HeroImage}
        alt="Hero"
        sx={{ width: '100%', maxHeight: 400, objectFit: 'contain' }}
      />
    </Grid>
  </Grid>
);

export default HeroSection;
