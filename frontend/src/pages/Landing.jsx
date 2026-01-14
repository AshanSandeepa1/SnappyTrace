// src/pages/Landing.jsx
import { Box } from '@mui/material';
import HeroSection from '../components/landing/HeroSection';
import Features from '../components/landing/Features';
import HowItWorks from '../components/landing/HowItWorks';
import Benefits from '../components/landing/Benefits';
import WatermarkPreview from '../components/landing/WatermarkPreview';
import Testimonials from '../components/landing/Testimonials';

const Landing = () => (
  <Box>
    <HeroSection />
    <WatermarkPreview />
    <Features />
    <HowItWorks />
    <Benefits />
    <Testimonials />
  </Box>
);

export default Landing;
