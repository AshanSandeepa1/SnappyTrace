import { Box, Container, Grid, Typography, useTheme } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import FingerprintIcon from '@mui/icons-material/Fingerprint';
import VerifiedIcon from '@mui/icons-material/Verified';
import FadeInSection from '../common/FadeInSection';

const steps = [
  {
    icon: <CloudUploadIcon sx={{ fontSize: 48 }} />,
    title: '1. Upload Your Content',
    description: 'Select images, videos, or documents to protect.',
  },
  {
    icon: <FingerprintIcon sx={{ fontSize: 48 }} />,
    title: '2. Embed AI Watermark',
    description: 'We apply a secure, invisible watermark using AI.',
  },
  {
    icon: <VerifiedIcon sx={{ fontSize: 48 }} />,
    title: '3. Verify Ownership',
    description: 'Instantly confirm authenticity or detect tampering.',
  },
];

const HowItWorks = () => {
  const theme = useTheme();

  return (
    <Box sx={{ py: 10, backgroundColor: theme.palette.mode === 'dark' ? '#111' : '#f9f9f9' }}>
      <Container>
        <FadeInSection>
          <Typography variant="h4" align="center" fontWeight="bold" gutterBottom>
            How It Works
          </Typography>
          <Typography variant="subtitle1" align="center" sx={{ color: 'text.secondary', mb: 6 }}>
            Protect your media in just three simple steps.
          </Typography>
        </FadeInSection>

        <Grid container spacing={4} justifyContent="center">
          {steps.map((step, index) => (
            <Grid
              key={index}
              item
              xs={12}
              sm={6}
              md={4}
              sx={{ display: 'flex', justifyContent: 'center' }}
            >
              <FadeInSection delay={index * 0.15}>
                <Box
                  textAlign="center"
                  px={3}
                  sx={{
                    maxWidth: 320,
                    '&:hover': {
                      transform: 'scale(1.03)',
                      transition: '0.3s ease',
                    },
                  }}
                >
                  <Box color="primary.main" mb={2}>
                    {step.icon}
                  </Box>
                  <Typography variant="h6" fontWeight="bold" gutterBottom>
                    {step.title}
                  </Typography>
                  <Typography color="text.secondary">{step.description}</Typography>
                </Box>
              </FadeInSection>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};

export default HowItWorks;
