import axios from 'axios';

// Axios instance
const api = axios.create({
  baseURL: 'http://example.com/api',
});

// Interceptor to add auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Interfaces
interface User {
  id: string;
  name: string;
  email: string;
}

interface Event {
  id: string;
  title: string;
  description: string;
  startTime: Date;
  endTime: Date;
}

interface Invitation {
  id: string;
  eventId: string;
  userId: string;
  status: 'pending' | 'accepted' | 'declined';
}

interface Reminder {
  id: string;
  eventId: string;
  message: string;
  remindAt: Date;
}

// CRUD for Event
const createEvent = async (event: Omit<Event, 'id'>) => {
  try {
    const response = await api.post<Event>('/events', event);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const getEvent = async (id: string) => {
  try {
    const response = await api.get<Event>(`/events/${id}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const updateEvent = async (id: string, event: Partial<Event>) => {
  try {
    const response = await api.patch<Event>(`/events/${id}`, event);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const deleteEvent = async (id: string) => {
  try {
    await api.delete(`/events/${id}`);
  } catch (error) {
    throw error;
  }
};

// CRUD for Invitation
const createInvitation = async (invitation: Omit<Invitation, 'id'>) => {
  try {
    const response = await api.post<Invitation>('/invitations', invitation);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const getInvitation = async (id: string) => {
  try {
    const response = await api.get<Invitation>(`/invitations/${id}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const updateInvitation = async (id: string, invitation: Partial<Invitation>) => {
  try {
    const response = await api.patch<Invitation>(`/invitations/${id}`, invitation);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const deleteInvitation = async (id: string) => {
  try {
    await api.delete(`/invitations/${id}`);
  } catch (error) {
    throw error;
  }
};

// CRUD for Reminder
const createReminder = async (reminder: Omit<Reminder, 'id'>) => {
  try {
    const response = await api.post<Reminder>('/reminders', reminder);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const getReminder = async (id: string) => {
  try {
    const response = await api.get<Reminder>(`/reminders/${id}`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const updateReminder = async (id: string, reminder: Partial<Reminder>) => {
  try {
    const response = await api.patch<Reminder>(`/reminders/${id}`, reminder);
    return response.data;
  } catch (error) {
    throw error;
  }
};

const deleteReminder = async (id: string) => {
  try {
    await api.delete(`/reminders/${id}`);
  } catch (error) {
    throw error;
  }
};

export {
  createEvent,
  getEvent,
  updateEvent,
  deleteEvent,
  createInvitation,
  getInvitation,
  updateInvitation,
  deleteInvitation,
  createReminder,
  getReminder,
  updateReminder,
  deleteReminder,
};