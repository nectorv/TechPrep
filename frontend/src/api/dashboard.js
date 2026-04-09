import { api } from './client'

export const dashboardApi = {
  getOverview:       (planId) => api.get(`/dashboard/overview?plan_id=${planId}`),
  getThemes:         (planId) => api.get(`/dashboard/themes?plan_id=${planId}`),
  getHeatmap:        (planId) => api.get(`/dashboard/heatmap?plan_id=${planId}`),
  getRecentSessions: (planId) => api.get(`/dashboard/recent-sessions?plan_id=${planId}`),
}
