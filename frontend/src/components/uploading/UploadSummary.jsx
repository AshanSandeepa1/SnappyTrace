import { Paper, Typography, Button, Box } from '@mui/material';

const UploadSummary = ({ result, onReupload }) => {
  return (
    <Paper sx={{ p: 3 }} elevation={2}>
      <Typography variant="h6" color="primary" gutterBottom>
        ✅ Upload Complete
      </Typography>
      <Typography variant="body2">Filename: <b>{result.filename}</b></Typography>
      <Typography variant="body2">Watermark ID: <b>{result.watermarkId}</b></Typography>
      {result.watermarkCode && (
        <Typography variant="body2">Watermark Code: <b>{result.watermarkCode}</b></Typography>
      )}
      <Typography variant="body2" sx={{ mb: 2 }}>{result.message}</Typography>

      <Box display="flex" gap={2}>
        {result.downloadUrl && (
          <Button
            variant="contained"
            color="primary"
            href={result.downloadUrl}
            target="_blank"
            rel="noopener"
          >
            Download Watermarked File
          </Button>
        )}
        <Button variant="outlined" onClick={onReupload}>
          Upload Another
        </Button>
      </Box>
    </Paper>
  );
};

export default UploadSummary;
