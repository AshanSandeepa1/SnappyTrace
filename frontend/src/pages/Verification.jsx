import { Container, Typography, TextField, Button, Box } from '@mui/material';
import { useState } from 'react';

const Verification = () => {
  const [id, setId] = useState('');
  const handleVerify = () => {
    // placeholder action
    alert(`Verifying ${id}`);
  };
  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Verify Ownership
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          label="File ID"
          variant="outlined"
          value={id}
          onChange={(e) => setId(e.target.value)}
          fullWidth
        />
        <Button variant="contained" onClick={handleVerify}>
          Verify
        </Button>
      </Box>
    </Container>
  );
};

export default Verification;
