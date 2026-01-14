import {
  Box,
  Container,
  IconButton,
  Paper,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { ChevronLeft, ChevronRight } from '@mui/icons-material';
import { useRef, useEffect } from 'react';
import FadeInSection from '../common/FadeInSection';

const testimonials = [
  {
    name: 'Alex Johnson',
    role: 'Digital Artist',
    quote:
      'SnappyTrace gives me peace of mind. I can finally share my work online without worrying about theft.',
  },
  {
    name: 'Maria Chen',
    role: 'Video Producer',
    quote:
      'The watermarking process is seamless and secure. It saved me during a copyright dispute.',
  },
  {
    name: 'Rahul Mehta',
    role: 'Content Manager',
    quote:
      'The dashboard is intuitive and the verification tool works like magic. A must-have for creators.',
  },
  {
    name: 'Sophie Kim',
    role: 'NFT Creator',
    quote: 'This tool is essential for proving authenticity in my NFT drops.',
  },
  {
    name: 'Daniel Reed',
    role: 'Photographer',
    quote: 'With SnappyTrace, I can now track stolen content with confidence.',
  },
];

const Testimonials = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const scrollRef = useRef(null);
  const autoScrollRef = useRef(null);

  useEffect(() => {
    autoScrollRef.current = setInterval(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollBy({ left: 320, behavior: 'smooth' });
      }
    }, 5000);

    return () => clearInterval(autoScrollRef.current);
  }, []);

  const handleScroll = (direction) => {
    if (!scrollRef.current) return;
    const scrollAmount = direction === 'left' ? -320 : 320;
    scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
  };

  return (
    <Box
      sx={{
        py: 10,
        backgroundColor: theme.palette.mode === 'dark' ? '#0d0d0d' : '#ffffff',
      }}
    >
      <Container>
        <FadeInSection>
          <Typography variant="h4" fontWeight="bold" align="center" gutterBottom>
            Trusted by Creators & Teams
          </Typography>
          <Typography variant="subtitle1" align="center" sx={{ color: 'text.secondary', mb: 4 }}>
            Here's what our users say about SnappyTrace.
          </Typography>
        </FadeInSection>

        <Box
          sx={{
            position: 'relative',
            overflow: 'visible',
            mt: 4,
          }}
        >
          {/* Left Arrow */}
          <IconButton
            onClick={() => handleScroll('left')}
            sx={{
              position: 'absolute',
              top: '50%',
              left: { xs: 8, sm: -28 },
              transform: 'translateY(-50%)',
              zIndex: 2,
              backgroundColor: theme.palette.background.paper,
              boxShadow: 2,
              '&:hover': { backgroundColor: theme.palette.grey[300] },
            }}
          >
            <ChevronLeft />
          </IconButton>

          {/* Scrollable Row */}
          <Box
            ref={scrollRef}
            onMouseEnter={() => clearInterval(autoScrollRef.current)}
            onMouseLeave={() => {
              autoScrollRef.current = setInterval(() => {
                scrollRef.current.scrollBy({ left: 320, behavior: 'smooth' });
              }, 5000);
            }}
            sx={{
              display: 'flex',
              gap: 3,
              overflowX: 'scroll',
              scrollSnapType: 'x mandatory',
              scrollBehavior: 'smooth',
              px: 3,
              py: 2,
              scrollbarWidth: 'none',
              '&::-webkit-scrollbar': { display: 'none' },
            }}
          >
            {testimonials.map((t, i) => (
              <FadeInSection key={i} delay={i * 0.15}>
                <Paper
                  sx={{
                    minWidth: isMobile ? '90vw' : 320,
                    maxWidth: 360,
                    height: 240,
                    p: 4,
                    borderRadius: 3,
                    flexShrink: 0,
                    scrollSnapAlign: 'start',
                    backgroundColor: theme.palette.background.paper,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                  elevation={3}
                >
                  <Typography variant="body1" sx={{ fontStyle: 'italic', mb: 2 }}>
                    “{t.quote}”
                  </Typography>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {t.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t.role}
                    </Typography>
                  </Box>
                </Paper>
              </FadeInSection>
            ))}
          </Box>

          {/* Right Arrow */}
          <IconButton
            onClick={() => handleScroll('right')}
            sx={{
              position: 'absolute',
              top: '50%',
              right: { xs: 8, sm: -28 },
              transform: 'translateY(-50%)',
              zIndex: 2,
              backgroundColor: theme.palette.background.paper,
              boxShadow: 2,
              '&:hover': { backgroundColor: theme.palette.grey[300] },
            }}
          >
            <ChevronRight />
          </IconButton>
        </Box>
      </Container>
    </Box>
  );
};

export default Testimonials;
