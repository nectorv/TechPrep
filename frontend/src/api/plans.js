import { api } from './client'

export const plansApi = {
  list:   ()           => api.get('/plans/'),
  create: (name, description) => api.post('/plans/', { name, description }),
  get:    (id)         => api.get(`/plans/${id}`),
  update: (id, name, description) => api.patch(`/plans/${id}`, { name, description }),
  delete: (id)         => api.delete(`/plans/${id}`),
}
