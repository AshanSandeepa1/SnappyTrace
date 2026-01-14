import { Box, Container, Grid, Typography, useTheme } from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import InsightsIcon from '@mui/icons-material/Insights';
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions';
import FadeInSection from '../common/FadeInSection';

const benefits = [
  {
    icon: <GavelIcon sx={{ fontSize: 40 }} />,
    title: 'Legal Protection',
    description: 'Provide verifiable proof of content ownership for legal or copyright claims.',
  },
  {
    icon: <InsightsIcon sx={{ fontSize: 40 }} />,
    title: 'Peace of Mind',
    description: 'Get notified of tampering attempts and verify authenticity instantly.',
  },
  {
    icon: <IntegrationInstructionsIcon sx={{ fontSize: 40 }} />,
    title: 'Easy Integration',
    description: 'Seamlessly manage your media through an intuitive dashboard.',
  },
];

const Benefits = () => {
  const theme = useTheme();

  return (
    <Box sx={{ py: 10, backgroundColor: theme.palette.background.default }}>
      <Container>
        <FadeInSection>
          <Typography variant="h4" align="center" fontWeight="bold" gutterBottom>
            Why Use SnappyTrace?
          </Typography>
          <Typography variant="subtitle1" align="center" sx={{ color: 'text.secondary', mb: 6 }}>
            Secure your digital assets with confidence.
          </Typography>
        </FadeInSection>

        <Grid container spacing={4} justifyContent="center">
          {benefits.map((b, i) => (
            <Grid
              key={i}
              item
              xs={12}
              sm={6}
              md={4}
              sx={{ display: 'flex', justifyContent: 'center' }}
            >
              <FadeInSection delay={i * 0.15}>
                <Box
                  textAlign="center"
                  px={2}
                  sx={{
                    maxWidth: 320,
                    '&:hover': {
                      transform: 'scale(1.03)',
                      transition: '0.3s ease',
                    },
                  }}
                >
                  <Box color="primary.main" mb={2}>
                    {b.icon}
                  </Box>
                  <Typography variant="h6" fontWeight="bold" gutterBottom>
                    {b.title}
                  </Typography>
                  <Typography color="text.secondary">{b.description}</Typography>
                </Box>
              </FadeInSection>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};

export default Benefits;
