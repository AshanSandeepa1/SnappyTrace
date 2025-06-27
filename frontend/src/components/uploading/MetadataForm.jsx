import {
  Box,
  TextField,
  Typography,
  Paper
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';

const MetadataForm = ({ file, metadata, onChange }) => {
  return (
    <Paper sx={{ p: 3, mb: 3 }} elevation={2}>
      <Typography variant="body1" fontWeight="bold" sx={{ mb: 2 }}>
        File Selected: {file.name}
      </Typography>

      <TextField
        label="Title"
        fullWidth
        sx={{ mb: 2 }}
        value={metadata.title}
        onChange={onChange('title')}
        required
      />
      <TextField
        label="Author"
        fullWidth
        sx={{ mb: 2 }}
        value={metadata.author}
        onChange={onChange('author')}
        required
      />

      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <DatePicker
          label="Created Date *"
          value={metadata.createdDate ? new Date(metadata.createdDate) : null}
          onChange={(newDate) =>
            onChange('createdDate')({
              target: { value: newDate ? newDate.toISOString().split('T')[0] : '' }
            })
          }
          renderInput={(params) => (
            <TextField {...params} fullWidth sx={{ mb: 2 }} required />
          )}
        />
      </LocalizationProvider>

      <TextField
        label="Organization (optional)"
        fullWidth
        sx={{ mt: 2, mb: 1 }}
        value={metadata.organization}
        onChange={onChange('organization')}
      />
    </Paper>
  );
};

export default MetadataForm;
