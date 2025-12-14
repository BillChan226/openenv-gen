import React from 'react';
import { Card, Grid, Typography } from '@mui/material';
import { useHistory } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const history = useHistory();

  const navigationCards = [
    { title: 'Events', path: '/events' },
    { title: 'Invitations', path: '/invitations' },
    { title: 'Reminders', path: '/reminders' },
  ];

  const handleCardClick = (path: string) => {
    history.push(path);
  };

  return (
    <Grid container spacing={3}>
      {navigationCards.map((card, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          <Card
            sx={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
            onClick={() => handleCardClick(card.path)}
          >
            <Typography variant="h5" component="div">
              {card.title}
            </Typography>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default Dashboard;