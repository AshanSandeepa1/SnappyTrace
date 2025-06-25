import { Container, Typography } from '@mui/material';
import UploadDropzone from '../components/UploadDropzone';

const Upload = () => (
  <Container sx={{ py: 4 }}>
    <Typography variant="h5" gutterBottom>
      Upload File
    </Typography>
    <UploadDropzone />
  </Container>
);

export default Upload;
