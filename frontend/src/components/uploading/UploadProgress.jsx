import { Box, LinearProgress, Typography } from '@mui/material';

const UploadProgress = ({ progress }) => (
  <Box sx={{ mb: 3 }}>
    <Typography variant="body2" gutterBottom>
      Uploading... {progress}%
    </Typography>
    <LinearProgress variant="determinate" value={progress} />
  </Box>
);

export default UploadProgress;
