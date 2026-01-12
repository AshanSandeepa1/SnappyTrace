import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Divider,
  Paper,
  Alert,
  CircularProgress
} from '@mui/material';
import { useState, useRef } from 'react';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import api from '../services/api';

const Verification = () => {
  const [fileId, setFileId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef();

  const hasKey = (obj, key) => !!obj && Object.prototype.hasOwnProperty.call(obj, key);
  const displayValue = (v) => (v === undefined || v === null || v === '' ? '—' : String(v));

  const handleVerify = async () => {
    setError('');
    setResult(null);

    if (!fileId && !selectedFile) {
      setError('Please provide a watermark ID or upload a file.');
      return;
    }

    setLoading(true);
    try {
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const res = await api.post('/verify', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setResult(res.data);
      } else {
        const res = await api.get(`/verify/${encodeURIComponent(fileId.trim())}`);
        setResult(res.data);
      }
    } catch (err) {
      const msg =
        err.code === 'ECONNABORTED'
          ? 'Verification timed out. Please try again.'
          : err.response?.data?.detail ||
            err.response?.data?.message ||
            err.message ||
            'Verification failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
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
        {loading ? 'Verifying...' : 'Start Verification'}
      </Button>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
          <CircularProgress size={28} />
        </Box>
      )}

      {/* Result display */}
      {result && (
        <Paper sx={{ p: 3, mt: 2 }} elevation={3}>
          {result.valid ? (
            <>
              <Typography variant="h6" color="success.main" gutterBottom>
                Ownership Verified
              </Typography>
              {typeof result.confidence === 'number' && (
                <Typography><b>Confidence:</b> {(result.confidence * 100).toFixed(1)}%</Typography>
              )}
              {typeof result.tamper_suspected === 'boolean' && (
                <Typography><b>Tamper suspected:</b> {result.tamper_suspected ? 'Yes' : 'No'}</Typography>
              )}
              {result.watermark_code && <Typography><b>Watermark Code:</b> {result.watermark_code}</Typography>}
              {result.watermark_id && <Typography><b>Watermark ID:</b> {result.watermark_id}</Typography>}
              {(result.owner?.name || result.owner?.email) && (
                <Typography>
                  <b>Owner:</b> {result.owner?.name ? `${result.owner.name} ` : ''}{result.owner?.email ? `<${result.owner.email}>` : ''}
                </Typography>
              )}
              {result.metadata?.author && <Typography><b>Author (metadata):</b> {result.metadata.author}</Typography>}
              {result.metadata?.title && <Typography><b>Title (metadata):</b> {result.metadata.title}</Typography>}
              {hasKey(result.metadata, 'organization') && (
                <Typography><b>Organization (metadata):</b> {displayValue(result.metadata.organization)}</Typography>
              )}
              {result.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.metadata.createdDate}</Typography>}
              {result.issued_at && <Typography><b>Issued:</b> {new Date(result.issued_at).toLocaleString()}</Typography>}
              {result.note && (
                <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                  {result.note}
                </Typography>
              )}
            </>
          ) : (result.method === 'perceptual_pdf' && (result.owner?.name || result.owner?.email)) ? (
            <>
              <Typography variant="h6" color="warning.main" gutterBottom>
                Ownership Match (Not Authoritative)
              </Typography>
              {typeof result.ownership_confidence === 'number' && (
                <Typography><b>Confidence:</b> {(result.ownership_confidence * 100).toFixed(1)}%</Typography>
              )}
              {typeof result.tamper_suspected === 'boolean' && (
                <Typography><b>Tamper suspected:</b> {result.tamper_suspected ? 'Yes' : 'No'}</Typography>
              )}
              {result.watermark_code && <Typography><b>Watermark Code:</b> {result.watermark_code}</Typography>}
              {result.watermark_id && <Typography><b>Watermark ID:</b> {result.watermark_id}</Typography>}
              {(result.owner?.name || result.owner?.email) && (
                <Typography>
                  <b>Owner:</b> {result.owner?.name ? `${result.owner.name} ` : ''}{result.owner?.email ? `<${result.owner.email}>` : ''}
                </Typography>
              )}
              {result.metadata?.author && <Typography><b>Author (metadata):</b> {result.metadata.author}</Typography>}
              {result.metadata?.title && <Typography><b>Title (metadata):</b> {result.metadata.title}</Typography>}
              {hasKey(result.metadata, 'organization') && (
                <Typography><b>Organization (metadata):</b> {displayValue(result.metadata.organization)}</Typography>
              )}
              {result.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.metadata.createdDate}</Typography>}
              {result.issued_at && <Typography><b>Issued:</b> {new Date(result.issued_at).toLocaleString()}</Typography>}
              {result.note && (
                <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                  {result.note}
                </Typography>
              )}
            </>
          ) : (
            <>
              <Typography variant="h6" color="error" gutterBottom>
                Verification failed
              </Typography>
              <Typography color="text.secondary">
                {result.reason || 'No watermark found or file is tampered.'}
              </Typography>

              {result.fallback?.match && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="warning">
                    Watermark could not be decoded, but a possible match was found via perceptual similarity.
                    (dHash distance: {result.fallback.hamming_distance})
                  </Alert>
                  {result.fallback.note && (
                    <Typography sx={{ mt: 1 }} color="text.secondary" variant="body2">
                      {result.fallback.note}
                    </Typography>
                  )}
                  {result.fallback.owner?.name || result.fallback.owner?.email ? (
                    <Typography sx={{ mt: 1 }}>
                      <b>Owner:</b> {result.fallback.owner?.name ? `${result.fallback.owner.name} ` : ''}
                      {result.fallback.owner?.email ? `<${result.fallback.owner.email}>` : ''}
                    </Typography>
                  ) : null}
                  {result.fallback.metadata?.author && <Typography><b>Author (metadata):</b> {result.fallback.metadata.author}</Typography>}
                  {result.fallback.metadata?.title && <Typography><b>Title (metadata):</b> {result.fallback.metadata.title}</Typography>}
                  {hasKey(result.fallback.metadata, 'organization') && (
                    <Typography><b>Organization (metadata):</b> {displayValue(result.fallback.metadata.organization)}</Typography>
                  )}
                  {result.fallback.metadata?.createdDate && <Typography><b>Created Date (metadata):</b> {result.fallback.metadata.createdDate}</Typography>}
                  {result.fallback.issued_at && <Typography><b>Issued:</b> {new Date(result.fallback.issued_at).toLocaleString()}</Typography>}
                </Box>
              )}
            </>
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
