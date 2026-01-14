import { Box, Container, Grid, Typography, useTheme } from '@mui/material';
import ShieldIcon from '@mui/icons-material/Security';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import FadeInSection from '../common/FadeInSection';

const features = [
  {
    icon: <AutoFixHighIcon sx={{ fontSize: 40 }} />,
    title: 'Invisible Watermarking',
    description: 'Embed undetectable digital marks in your media using advanced AI.',
  },
  {
    icon: <ShieldIcon sx={{ fontSize: 40 }} />,
    title: 'Tamper Detection',
    description: 'Identify any unauthorized edits or watermark removals.',
  },
  {
    icon: <VisibilityIcon sx={{ fontSize: 40 }} />,
    title: 'Ownership Verification',
    description: 'Easily prove and verify content ownership across platforms.',
  },
];

const Features = () => {
  const theme = useTheme();

  return (
    <Box sx={{ py: 10, backgroundColor: theme.palette.background.default }}>
      <Container>
        <FadeInSection>
          <Typography variant="h4" align="center" fontWeight="bold" gutterBottom>
            What SnappyTrace Does
          </Typography>
          <Typography variant="subtitle1" align="center" sx={{ color: 'text.secondary', mb: 6 }}>
            Everything you need to protect and prove digital ownership.
          </Typography>
        </FadeInSection>

            <Grid container spacing={4} justifyContent="center">
                {features.map((feat, i) => (
                    <Grid
                    key={i}
                    item
                    xs={12}
                    sm={6}
                    md={4}
                    sx={{
                        display: 'flex',
                        justifyContent: 'center',
                    }}
                    >
                    <FadeInSection delay={i * 0.15}>
                        <Box
                        textAlign="center"
                        px={2}
                        sx={{
                            maxWidth: 320, // optional: keeps cards from being too wide
                            '&:hover': { transform: 'scale(1.03)', transition: '0.3s ease' },
                        }}
                        >
                        <Box color="primary.main" mb={2}>
                            {feat.icon}
                        </Box>
                        <Typography variant="h6" gutterBottom fontWeight="bold">
                            {feat.title}
                        </Typography>
                        <Typography color="text.secondary">{feat.description}</Typography>
                        </Box>
                    </FadeInSection>
        </Grid>
    ))}
    </Grid>

      </Container>
    </Box>
  );
};

export default Features;
