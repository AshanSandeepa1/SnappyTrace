import { Container, Typography, Alert, CircularProgress, Box } from '@mui/material';
import { useEffect, useState } from 'react';
import FileCard from '../components/FileCard';
import { useAuth } from '../store/AuthContext';
import api from '../services/api';

const Dashboard = () => {
  const { token } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setError('');
      setLoading(true);
      try {
        const res = await api.get('/my-files', {
          headers: {
            ...(token && { Authorization: `Bearer ${token}` })
          }
        });
        if (!mounted) return;
        setItems(res.data?.items || []);
      } catch (err) {
        if (!mounted) return;
        setError(err.response?.data?.detail || 'Failed to load uploads');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [token]);

  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Recent Uploads
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      ) : (
        items.length ? (
          items.map((f) => (
            <FileCard file={f} key={f.watermark_id} />
          ))
        ) : (
          <Typography variant="body2" color="text.secondary">
            No uploads yet.
          </Typography>
        )
      )}
    </Container>
  );
};

export default Dashboard;
