import { Container, Typography, Switch, FormControlLabel } from '@mui/material';
import { useThemeContext } from '../store/ThemeContext';

const Settings = () => {
  const { mode, toggle } = useThemeContext();
  return (
    <Container sx={{ py: 4 }}>
      <Typography variant="h5" gutterBottom>
        Settings
      </Typography>
      <FormControlLabel
        control={<Switch checked={mode === 'dark'} onChange={toggle} />}
        label="Dark Mode"
      />
    </Container>
  );
};

export default Settings;
