import { Card, CardContent, Typography } from '@mui/material';
import { motion } from 'framer-motion';

const FileCard = ({ file }) => (
  <Card component={motion.div} whileHover={{ scale: 1.02 }} sx={{ mb: 2 }}>
    <CardContent>
      <Typography variant="subtitle1" fontWeight="bold">
        {file.name}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Status: {file.status}
      </Typography>
    </CardContent>
  </Card>
);

export default FileCard;
