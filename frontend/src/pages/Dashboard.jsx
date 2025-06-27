import { Container, Typography } from '@mui/material';
import FileCard from '../components/FileCard';
import { useAuth } from '../store/AuthContext';

const sample = [
  { name: 'image.jpg', status: 'Verified' },
  { name: 'video.mp4', status: 'Pending' },
  { name: 'doc.pdf', status: 'Failed' },
];

const Dashboard = () => {
  const { user, isAuthenticated } = useAuth(); 

  console.log('Auth Status:', isAuthenticated);
  console.log('User:', user);

  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Recent Uploads
      </Typography>
      {sample.map((f, i) => (
        <FileCard file={f} key={i} />
      ))}
    </Container>
  );
};

export default Dashboard;
