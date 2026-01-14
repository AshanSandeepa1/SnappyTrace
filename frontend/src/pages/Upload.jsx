import {
  Container,
  Typography,
  Divider,
  Button,
  Box,
  Alert
} from '@mui/material';
import { useState } from 'react';
import FileUploadInput from '../components/uploading/FileUploadInput';
import MetadataForm from '../components/uploading/MetadataForm';
import UploadProgress from '../components/uploading/UploadProgress';
import UploadSummary from '../components/uploading/UploadSummary';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';

const Upload = () => {
  const { token } = useAuth();

  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [metadata, setMetadata] = useState({
    title: '',
    author: '',
    createdDate: '',
    organization: ''
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileChange = (file) => {
    setFile(file);
    setProgress(0);
    setResult(null);
    setError('');
  };

  const handleMetaChange = (field) => (valueOrEvent) => {
    const value = valueOrEvent?.target?.value ?? valueOrEvent;
    setMetadata((prev) => ({ ...prev, [field]: value }));
  };

  const validateMetadata = () => {
    if (!metadata.title.trim() || !metadata.author.trim() || !metadata.createdDate) {
      setError('Please fill in Title, Author, and Created Date.');
      return false;
    }
    return true;
  };

  const handleStartEmbedding = async () => {
    setError('');
    if (!file) return;
    if (!validateMetadata()) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', metadata.title);
    formData.append('author', metadata.author);
    formData.append('createdDate', metadata.createdDate);
    formData.append('organization', metadata.organization);

    try {
      setProgress(5);
      const res = await api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(token && { Authorization: `Bearer ${token}` })
        },
        onUploadProgress: (e) => {
          if (e.total) {
            const percent = Math.round((e.loaded * 100) / e.total);
            setProgress(percent);
          }
        }
      });

      setProgress(100);
      setResult({
        watermarkId: res.data.watermark_id,
        watermarkCode: res.data.watermark_code,
        message: res.data.message,
        filename: res.data.original_filename,
        downloadUrl: res.data.download_url
      });
    } catch (err) {
      setProgress(0);
      const msg = err.response?.data?.detail || 'Upload failed. Please try again.';
      setError(msg);
    }
  };

  const handleReupload = () => {
    setFile(null);
    setProgress(0);
    setResult(null);
    setError('');
  };

  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Upload & Watermark Your File
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!file && <FileUploadInput onChange={handleFileChange} />}

      {file && !result && (
        <>
          <MetadataForm file={file} metadata={metadata} onChange={handleMetaChange} />
          <Box textAlign="right" mb={3}>
            <Button variant="contained" onClick={handleStartEmbedding}>
              Start Embedding
            </Button>
          </Box>
        </>
      )}

      {progress > 0 && <UploadProgress progress={progress} />}

      {result && <UploadSummary result={result} onReupload={handleReupload} />}

      <Divider sx={{ my: 4 }}>Learn More</Divider>
      <Typography variant="body2" color="text.secondary">
        🧠 <b>How watermarking works:</b> We embed invisible digital ownership info into your file using a secure, tamper-detectable process. <br /> This ensures your ownership is preserved even if the file is modified.
      </Typography>
    </Container>
  );
};

export default Upload;
