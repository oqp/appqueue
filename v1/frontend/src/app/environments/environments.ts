export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',  // URL del backend FastAPI
  appName: 'Sistema de Tickets',
  version: '1.0.0',

  // Configuración de autenticación
  auth: {
    tokenRefreshInterval: 5 * 60 * 1000, // 5 minutos antes de expirar
    sessionTimeout: 30 * 60 * 1000, // 30 minutos de inactividad
  },

  // Configuración de WebSocket
  websocket: {
    url: 'ws://localhost:8000/ws',
    reconnectInterval: 5000,
    maxReconnectAttempts: 5
  },
  printServiceUrl: 'http://localhost:9000/api'
};
