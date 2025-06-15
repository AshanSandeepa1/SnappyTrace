import { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, Typography } from '@mui/material';

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    axios.get('http://localhost:8000/')
      .then(res => setMessage(res.data.message))
      .catch(err => setMessage("Failed to connect to backend."));
  }, []);

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        SnappyTrace Frontend
      </Typography>
      <Typography variant="body1">
        Backend says: {message}
      </Typography>
    </Container>
  );
}

export default App;
