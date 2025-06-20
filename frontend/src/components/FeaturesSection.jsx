import { Box, Container, Grid, Typography } from '@mui/material';

const features = [
  {
    icon: '🔒',
    title: 'Invisible Watermarks',
    description: 'Embed watermarks that cannot be detected or removed easily.',
  },
  {
    icon: '⚡',
    title: 'Fast Verification',
    description: 'Verify ownership instantly with AI-powered algorithms.',
  },
  {
    icon: '🛡️',
    title: 'Tamper Detection',
    description: 'Detect any unauthorized alteration or removal of watermarks.',
  },
  {
    icon: '☁️',
    title: 'Cloud Storage',
    description: 'Securely manage and access your files from anywhere.',
  },
];

const FeaturesSection = () => (
  <Box sx={{ py: 8 }}>
    <Container maxWidth="lg">
      <Typography variant="h4" fontWeight="bold" mb={4} textAlign="center">
        Features
      </Typography>
      <Grid container spacing={4}>
        {features.map((feature, i) => (
          <Grid item xs={12} md={3} key={i}>
            <Box
              sx={{
                p: 3,
                borderRadius: 2,
                boxShadow: 3,
                textAlign: 'center',
                height: '100%',
              }}
            >
              <Typography variant="h2" component="div" mb={1}>
                {feature.icon}
              </Typography>
              <Typography variant="h6" fontWeight="bold" mb={1}>
                {feature.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {feature.description}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Container>
  </Box>
);

export default FeaturesSection;
