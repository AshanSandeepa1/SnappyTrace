import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Divider,
  Paper,
  Alert
} from '@mui/material';
import { useState, useRef } from 'react';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import api from '../services/api';

const Verification = () => {
  const [fileId, setFileId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileInputRef = useRef();

  const handleVerify = async () => {
    setError('');
    setResult(null);

    if (!fileId && !selectedFile) {
      setError('Please provide a watermark ID or upload a file.');
      return;
    }

    // Fake logic for now; replace with API call
    setTimeout(() => {
      if (fileId === 'WMK-4106B40E' || (selectedFile && selectedFile.name.includes('3'))) {
        setResult({
          valid: true,
          fileName: selectedFile?.name || '3.png',
          matchedId: 'WMK-4106B40E',
          owner: 'John Derik',
          timestamp: '2025-06-25 10:45 AM'
        });
      } else {
        setResult({ valid: false });
      }
    }, 1000);
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setFileId('');
    setResult(null);
    setError('');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setSelectedFile(file);
      setFileId('');
      setResult(null);
      setError('');
    }
  };

  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Verify Digital Ownership
      </Typography>
      <Typography variant="body2" sx={{ mb: 2 }} color="text.secondary">
        Paste a Watermark ID or upload a file to verify authenticity.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* ID Input */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          label="Watermark ID"
          variant="outlined"
          value={fileId}
          onChange={(e) => setFileId(e.target.value)}
          fullWidth
        />
      </Box>

      {/* Drag-and-drop upload */}
      <Box
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        sx={{
          border: '2px dashed gray',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          mb: 2,
          backgroundColor: '#f9f9f9',
          cursor: 'pointer'
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <CloudUploadIcon fontSize="large" color="action" />
        <Typography variant="body2" color="text.secondary">
          Drag & drop your file here or click to upload
        </Typography>
        <input
          type="file"
          hidden
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*,application/pdf,video/*"
        />
      </Box>

      {selectedFile && (
        <Typography variant="body2" sx={{ mb: 2 }}>
          Selected File: <strong>{selectedFile.name}</strong>
        </Typography>
      )}

      <Button variant="contained" onClick={handleVerify} sx={{ mb: 3 }}>
        Start Verification
      </Button>

      {/* Result display */}
      {result && (
        <Paper sx={{ p: 3, mt: 2 }} elevation={3}>
          {result.valid ? (
            <>
              <Typography variant="h6" color="success.main" gutterBottom>
                ✅ Ownership Verified
              </Typography>
              <Typography><b>File Name:</b> {result.fileName}</Typography>
              <Typography><b>Watermark ID:</b> {result.matchedId}</Typography>
              <Typography><b>Owner:</b> {result.owner}</Typography>
              <Typography><b>Issued:</b> {result.timestamp}</Typography>
            </>
          ) : (
            <Typography variant="h6" color="error">
              ❌ Verification failed — No watermark found or file is tampered.
            </Typography>
          )}
        </Paper>
      )}

      <Divider sx={{ my: 4 }}>Why Verification?</Divider>
      <Typography variant="body2" color="text.secondary">
        Verification ensures your file hasn’t been tampered with and confirms the embedded watermark ID.
        SnappyTrace uses both visible and invisible watermarking techniques powered by AI to prove authenticity.
      </Typography>
    </Container>
  );
};

export default Verification;
