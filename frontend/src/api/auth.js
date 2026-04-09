import { api } from './client'

export const authApi = {
  register:               (email, password) => api.post('/auth/register', { email, password }),
  login:                  (email, password) => api.postForm('/auth/login', { username: email, password }),
  generateTelegramCode:   ()                => api.post('/auth/telegram-link-code'),
}
