import { Card, CardContent, Typography, Box } from '@mui/material';
import { motion } from 'framer-motion';

const FileCard = ({ file }) => (
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
    </CardContent>
  </Card>
);

export default FileCard;
