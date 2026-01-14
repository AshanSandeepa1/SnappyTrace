import { Box, Container, Typography, useTheme, useMediaQuery } from '@mui/material';
import FadeInSection from '../common/FadeInSection';
import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import { useRef } from 'react';

const WatermarkPreview = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const containerRef = useRef();
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  });

  // Scale from 1 to 1.15 as user scrolls down this section
  const scale = useSpring(useTransform(scrollYProgress, [0, 1], [1, 1.25]), {
    stiffness: 100,
    damping: 20,
  });

  return (
    <Box
      ref={containerRef}
      sx={{
        py: 10,
        backgroundColor: isDark ? '#1a1a1a' : '#f5f5f5',
        textAlign: 'center',
      }}
    >
      <Container>
        <FadeInSection>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            See SnappyTrace in Action
          </Typography>
          <Typography variant="subtitle1" sx={{ color: 'text.secondary', mb: 4 }}>
            Invisible watermarking that doesn't alter your visual content — but secures your rights.
          </Typography>
        </FadeInSection>

        <motion.div style={{ scale, originX: 0.5, originY: 0.5 }}>
          <Box
            component="video"
            src="/WatermarkPreview.webm"
            autoPlay
            muted
            loop
            playsInline
            sx={{
              width: '100%',
              maxWidth: 800,
              borderRadius: 2,
              boxShadow: 3,
              mx: 'auto',
              display: 'block',
            }}
          />
        </motion.div>
      </Container>
    </Box>
  );
};

export default WatermarkPreview;
