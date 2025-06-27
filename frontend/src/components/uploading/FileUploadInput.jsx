import { Box } from '@mui/material';

const FileUploadInput = ({ onChange }) => (
  <Box
    component="input"
    type="file"
    onChange={(e) => onChange(e.target.files[0])}
    accept="image/*,video/*,.pdf,.doc,.docx"
    sx={{
      width: '100%',
      border: '2px dashed',
      p: 4,
      borderRadius: 2,
      textAlign: 'center',
      cursor: 'pointer',
      mb: 3,
    }}
  />
);

export default FileUploadInput;
