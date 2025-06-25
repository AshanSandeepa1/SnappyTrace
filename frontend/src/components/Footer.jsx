import {
  Box,
  Container,
  Grid,
  Typography,
  Link as MuiLink,
  IconButton,
  useTheme,
  useMediaQuery,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import {
  LinkedIn,
  Facebook,
  YouTube,
  GitHub,
  SportsBasketball,
  ArrowUpward,
  ExpandMore,
} from '@mui/icons-material';
import { useState, useEffect } from 'react';

const Footer = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const [showScrollTop, setShowScrollTop] = useState(false);
  useEffect(() => {
    const handleScroll = () => {
      const halfway = window.innerHeight / 2;
      setShowScrollTop(window.scrollY > halfway);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const linkGroup = (title, links) => (
    <>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        {title}
      </Typography>
      <Typography component="div" variant="body2">
        {links.map((text, i) => (
          <MuiLink
            key={i}
            href="#"
            underline="none"
            color="text.secondary"
            display="block"
            sx={{ mb: 1 }}
          >
            {text}
          </MuiLink>
        ))}
      </Typography>
    </>
  );

  return (
    <Box
      component="footer"
      sx={{
        pt: 10,
        pb: 6,
        backgroundColor: theme.palette.background.default,
        borderTop: `1px solid ${theme.palette.divider}`,
      }}
    >
      <Container maxWidth="lg">
        <Grid
          container
          spacing={4}
          justifyContent="space-between"
          alignItems="flex-start"
        >
          {/* Branding Column */}
          <Grid item xs={12} md={4}>
            <Box>
              <Box display="flex" alignItems="center" mb={1}>
                <img
                  src="/logo.svg"
                  alt="SnappyTrace"
                  style={{ height: 32, marginRight: 8 }}
                />
                <Typography variant="h6" fontWeight="bold">
                  SnappyTrace
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                v1.2.0
              </Typography>
              <Typography
                variant="body2"
                sx={{ mb: 2, color: 'text.secondary' }}
              >
                Secure your content with AI watermarking and tamper detection.
              </Typography>
              <Typography variant="body2">🔹 React Material UI v7</Typography>
              <Typography variant="body2">🔹 Dark Mode Supported</Typography>
              <Typography variant="body2">🔹 Documentation</Typography>
            </Box>
          </Grid>

          {/* Collapsible on Mobile, Normal Grid on Desktop */}
          {isMobile ? (
            <Grid item xs={12}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography fontWeight="bold">Company</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {linkGroup('Company', ['About', 'Contact', 'Why SnappyTrace?'])}
                </AccordionDetails>
              </Accordion>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography fontWeight="bold">Support</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {linkGroup('Support', ['Pricing', 'FAQ', 'License Terms', 'Discord'])}
                </AccordionDetails>
              </Accordion>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography fontWeight="bold">Resources</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {linkGroup('Resources', ['Blog', 'Freebies', 'Privacy Policy', 'Refund Policy'])}
                </AccordionDetails>
              </Accordion>
            </Grid>
          ) : (
            <Grid item xs={12} md={8}>
              <Grid container spacing={4} justifyContent="flex-end">
                <Grid item xs={12} sm={4} md={3}>
                  {linkGroup('Company', ['About', 'Contact', 'Why SnappyTrace?'])}
                </Grid>
                <Grid item xs={12} sm={4} md={3}>
                  {linkGroup('Support', ['Pricing', 'FAQ', 'License Terms', 'Discord'])}
                </Grid>
                <Grid item xs={12} sm={4} md={3}>
                  {linkGroup('Resources', ['Blog', 'Freebies', 'Privacy Policy', 'Refund Policy'])}
                </Grid>
              </Grid>
            </Grid>
          )}
        </Grid>

        {/* Bottom bar */}
        <Box
          sx={{
            mt: 6,
            py: 2,
            px: 3,
            borderRadius: 4,
            backgroundColor:
              theme.palette.mode === 'dark' ? '#1a1a1a' : '#f4f6f8',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} SnappyTrace. All rights reserved.
          </Typography>
          <Box>
            <IconButton color="primary" size="small">
              <LinkedIn />
            </IconButton>
            <IconButton color="primary" size="small">
              <Facebook />
            </IconButton>
            <IconButton color="primary" size="small">
              <YouTube />
            </IconButton>
            <IconButton color="primary" size="small">
              <GitHub />
            </IconButton>
            <IconButton color="primary" size="small">
              <SportsBasketball />
            </IconButton>
          </Box>
        </Box>
      </Container>

      {/* Scroll to Top Button */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 50,
          right: 50,
          transition: 'opacity 0.3s ease, transform 0.3s ease',
          opacity: showScrollTop ? 1 : 0,
          transform: showScrollTop ? 'scale(1)' : 'scale(0.9)',
          pointerEvents: showScrollTop ? 'auto' : 'none',
          zIndex: 1000,
        }}
      >
        <IconButton
          onClick={scrollToTop}
          sx={{
            backgroundColor: theme.palette.primary.main,
            color: '#fff',
            '&:hover': {
              backgroundColor: theme.palette.primary.dark,
            },
            boxShadow: 4,
          }}
        >
          <ArrowUpward />
        </IconButton>
      </Box>
    </Box>
  );
};

export default Footer;
