import { Card, CardContent, Typography, Box, Button } from '@mui/material';
import { motion } from 'framer-motion';

const FileCard = ({ file }) => {
  // Backwards compatible: if an older backend doesn't send download_available,
  // fall back to showing the button when download_url exists.
  const canDownload = file.download_available ?? Boolean(file.download_url);

  return (
    <Card component={motion.div} whileHover={{ scale: 1.02 }} sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle1" fontWeight="bold">
          {file.original_filename || file.name}
        </Typography>

        <Box sx={{ mt: 0.5 }}>
          {file.watermark_code && (
            <Typography variant="body2" color="text.secondary">
              Watermark: {file.watermark_code}
            </Typography>
          )}
          {file.issued_at && (
            <Typography variant="body2" color="text.secondary">
              Issued: {new Date(file.issued_at).toLocaleString()}
            </Typography>
          )}
        </Box>

        <Box sx={{ mt: 1 }}>
          {canDownload && file.download_url ? (
            <Button
              variant="outlined"
              href={file.download_url}
              target="_blank"
              rel="noopener"
            >
              Download
            </Button>
          ) : (
            <Typography variant="caption" color="text.secondary">
              Download unavailable (temporary storage)
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default FileCard;
