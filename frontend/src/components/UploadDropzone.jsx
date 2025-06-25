import { useState } from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import { motion } from 'framer-motion';

const UploadDropzone = ({ onUpload }) => {
  const [progress, setProgress] = useState(0);

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    onUpload?.(file);
    setProgress(10);
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(interval);
          return 100;
        }
        return p + 10;
      });
    }, 200);
  };

  return (
    <Box component={motion.div} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Box
        component="input"
        type="file"
        onChange={handleChange}
        sx={{
          width: '100%',
          border: '2px dashed',
          p: 4,
          borderRadius: 2,
          textAlign: 'center',
          cursor: 'pointer',
        }}
      />
      {progress > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" gutterBottom>
            Uploading... {progress}%
          </Typography>
          <LinearProgress variant="determinate" value={progress} />
        </Box>
      )}
    </Box>
  );
};

export default UploadDropzone;
