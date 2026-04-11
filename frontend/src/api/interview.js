import { api } from './client'

export const interviewApi = {
  startSession:  (type, planId)                    => api.post('/interview/sessions', { type, plan_id: planId }),
  submitAnswer:  (sessionId, question_id, content, is_retry = false) =>
    api.post(`/interview/sessions/${sessionId}/answer`, { question_id, content, is_retry }),
  endSession:    (sessionId)                       => api.post(`/interview/sessions/${sessionId}/end`, {}),
  getReview:     (sessionId)                       => api.get(`/interview/sessions/${sessionId}/review`),
  getDueCount:   (planId)                          => api.get(`/interview/due-count?plan_id=${planId}`),
}
