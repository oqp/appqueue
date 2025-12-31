export const environment = {
  production: true,
  // Backend en dominio separado
  apiUrl: 'https://munoz.qxpertserver.ingenius.online',
  appName: 'Sistema de Tickets - AppQueue',
  version: '1.0.0',

  // Configuracion de autenticacion
  auth: {
    tokenRefreshInterval: 5 * 60 * 1000, // 5 minutos antes de expirar
    sessionTimeout: 30 * 60 * 1000, // 30 minutos de inactividad
  },

  // Configuracion de WebSocket
  websocket: {
    url: 'wss://munoz.qxpertserver.ingenius.online/ws',
    reconnectInterval: 5000,
    maxReconnectAttempts: 10
  },

  // Servicio de impresion local (configurar segun necesidad)
  printServiceUrl: ''
};
