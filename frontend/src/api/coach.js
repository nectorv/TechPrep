import { api } from './client'

export const coachApi = {
  getHistory:   (planId)           => api.get(`/coach/history?plan_id=${planId}`),
  chat:         (planId, content)  => api.post(`/coach/chat?plan_id=${planId}`, { content }),
  clearHistory: (planId)           => api.delete(`/coach/history?plan_id=${planId}`),
}
