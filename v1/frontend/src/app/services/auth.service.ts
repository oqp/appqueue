// auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, throwError, timer } from 'rxjs';
import { catchError, map, tap, switchMap } from 'rxjs/operators';
import {environment} from '../environments/environments';

// ========== INTERFACES MATCHING BACKEND SCHEMAS ==========

interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
  session_id: string;
  message: string;
}

interface RefreshTokenRequest {
  refresh_token: string;
}

interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

interface ResetPasswordRequest {
  email: string;
}

interface UserInfo {
  role_name: string;
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  role_id: number;
  is_active: boolean;
  station_id?: number;
  station_name?: string;
  permissions?: string[];
  last_login?: string;
  created_at: string;
}

interface TokenInfo {
  valid: boolean;
  expired: boolean;
  user_id?: string;
  username?: string;
  role?: string;
  expires_at?: string;
  issued_at?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: UserInfo | null;
  token: string | null;
  refreshToken: string | null;
  sessionId: string | null;
  expiresAt: Date | null;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/api/v1/auth`;

  // Estado de autenticación
  private authState = new BehaviorSubject<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
    refreshToken: null,
    sessionId: null,
    expiresAt: null
  });

  // Observables públicos
  public isAuthenticated$ = this.authState.asObservable().pipe(
    map(state => state.isAuthenticated)
  );

  public currentUser$ = this.authState.asObservable().pipe(
    map(state => state.user)
  );

  // Timer para refresh automático
  private refreshTokenTimer: any;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    // Inicializar estado desde localStorage
    this.initializeAuthState();
  }

  // ========== INICIALIZACIÓN ==========

  private initializeAuthState(): void {
    const token = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userStr = localStorage.getItem('user_info');
    const expiresAtStr = localStorage.getItem('token_expires_at');
    const sessionId = localStorage.getItem('session_id');

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);

        // IMPORTANTE: Normalizar el rol desde localStorage
        if (!user.role && user.role_name) {
          user.role = user.role_name;
        }

        const expiresAt = expiresAtStr ? new Date(expiresAtStr) : null;

        // Verificar si el token no ha expirado
        if (expiresAt && expiresAt > new Date()) {
          this.authState.next({
            isAuthenticated: true,
            user: user,
            token: token,
            refreshToken: refreshToken,
            sessionId: sessionId,
            expiresAt: expiresAt
          });

          // Programar refresh automático
          this.scheduleTokenRefresh();
        } else {
          // Token expirado, intentar refresh
          if (refreshToken) {
            this.refreshAccessToken().subscribe({
              error: () => this.clearAuthState()
            });
          } else {
            this.clearAuthState();
          }
        }
      } catch (error) {
        console.error('Error parsing auth state:', error);
        this.clearAuthState();
      }
    }
  }
  // ========== MÉTODOS DE AUTENTICACIÓN ==========

  /**
   * Login de usuario
   */
  login(username: string, password: string, rememberMe: boolean = false): Observable<LoginResponse> {
    const request: LoginRequest = {
      username,
      password,
      remember_me: rememberMe
    };

    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, request).pipe(
      tap(response => {
        this.handleLoginResponse(response);
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Logout de usuario
   */
  logout(): Observable<any> {
    const token = this.authState.value.token;
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    // Cancelar timer de refresh
    this.cancelTokenRefresh();

    return this.http.post(`${this.apiUrl}/logout`, {}, { headers }).pipe(
      tap(() => {
        this.clearAuthState();
        this.router.navigate(['/login']);
      }),
      catchError((error) => {
        // Limpiar estado aunque falle el logout en el servidor
        this.clearAuthState();
        this.router.navigate(['/login']);
        return throwError(() => error);
      })
    );
  }

  /**
   * Refresh del access token
   */
  refreshAccessToken(): Observable<RefreshTokenResponse> {
    const refreshToken = this.authState.value.refreshToken ||
      localStorage.getItem('refresh_token');

    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available'));
    }

    const request: RefreshTokenRequest = {
      refresh_token: refreshToken
    };

    return this.http.post<RefreshTokenResponse>(`${this.apiUrl}/refresh`, request).pipe(
      tap(response => {
        this.handleRefreshResponse(response);
      }),
      catchError((error) => {
        this.clearAuthState();
        this.router.navigate(['/login']);
        return throwError(() => error);
      })
    );
  }

  /**
   * Obtener información del usuario actual
   */
  getCurrentUserInfo(): Observable<UserInfo> {
    const headers = this.getAuthHeaders();

    return this.http.get<UserInfo>(`${this.apiUrl}/me`, { headers }).pipe(
      tap(user => {
        // Actualizar información del usuario en el estado
        const currentState = this.authState.value;
        this.authState.next({
          ...currentState,
          user: user
        });
        localStorage.setItem('user_info', JSON.stringify(user));
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Cambiar contraseña
   */
  changePassword(currentPassword: string, newPassword: string, confirmPassword: string): Observable<any> {
    const request: ChangePasswordRequest = {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword
    };

    const headers = this.getAuthHeaders();

    return this.http.post(`${this.apiUrl}/change-password`, request, { headers }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Solicitar reset de contraseña
   */
  requestPasswordReset(email: string): Observable<any> {
    const request: ResetPasswordRequest = {
      email: email
    };

    return this.http.post(`${this.apiUrl}/reset-password`, request).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Verificar token
   */
  verifyToken(): Observable<TokenInfo> {
    const headers = this.getAuthHeaders();

    return this.http.get<TokenInfo>(`${this.apiUrl}/verify-token`, { headers }).pipe(
      catchError(this.handleError)
    );
  }

  // ========== MÉTODOS DE UTILIDAD ==========

  /**
   * Obtener el usuario actual del estado
   */
  getCurrentUser(): UserInfo | null {
    const user = this.authState.value.user;

    // SIEMPRE normalizar el rol cuando se obtiene el usuario
    if (user) {
      if (!user.role && user.role_name) {
        user.role = user.role_name;
      }
    }

    return user;
  }

  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated(): boolean {
    return this.authState.value.isAuthenticated;
  }

  /**
   * Obtener el token actual
   */
  getToken(): string | null {
    return this.authState.value.token || localStorage.getItem('access_token');
  }

  /**
   * Obtener headers con autenticación
   */
  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Verificar si el usuario tiene un rol específico
   */
  hasRole(role: string): boolean {
    const user = this.authState.value.user;
    return user ? user.role === role : false;
  }

  /**
   * Verificar si el usuario tiene alguno de los roles especificados
   */
  hasAnyRole(roles: string[]): boolean {
    const user = this.authState.value.user;
    return user ? roles.includes(user.role) : false;
  }

  /**
   * Verificar si el usuario tiene un permiso específico
   */
  hasPermission(permission: string): boolean {
    const user = this.authState.value.user;
    return user && user.permissions ? user.permissions.includes(permission) : false;
  }

  // ========== MÉTODOS PRIVADOS ==========

  private handleLoginResponse(response: LoginResponse): void {
    const expiresAt = new Date();
    expiresAt.setSeconds(expiresAt.getSeconds() + response.expires_in);

    // Normalize user role
    const user = response.user;

    // IMPORTANTE: El backend envía role_name, copiarlo a role
    if (!user.role && user.role_name) {
      user.role = user.role_name;
    }

    // Log para verificar
    console.log('User after role normalization:', user);
    console.log('Role assigned:', user.role);

    // Normalize permissions if they come as JSON string
    if (user.permissions && typeof user.permissions === 'string') {
      try {
        user.permissions = JSON.parse(user.permissions);
      } catch (e) {
        console.error('Error parsing permissions:', e);
      }
    }

    // Actualizar estado
    this.authState.next({
      isAuthenticated: true,
      user: user,
      token: response.access_token,
      refreshToken: response.refresh_token,
      sessionId: response.session_id,
      expiresAt: expiresAt
    });

    // Guardar en localStorage
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    localStorage.setItem('user_info', JSON.stringify(user));
    localStorage.setItem('token_expires_at', expiresAt.toISOString());
    localStorage.setItem('session_id', response.session_id);

    // Programar refresh automático
    this.scheduleTokenRefresh();
  }

  private handleRefreshResponse(response: RefreshTokenResponse): void {
    const expiresAt = new Date();
    expiresAt.setSeconds(expiresAt.getSeconds() + response.expires_in);

    // Actualizar estado manteniendo la información del usuario
    const currentState = this.authState.value;
    this.authState.next({
      ...currentState,
      token: response.access_token,
      refreshToken: response.refresh_token,
      expiresAt: expiresAt
    });

    // Actualizar localStorage
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    localStorage.setItem('token_expires_at', expiresAt.toISOString());

    // Reprogramar refresh automático
    this.scheduleTokenRefresh();
  }

  private clearAuthState(): void {
    // Limpiar estado
    this.authState.next({
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
      sessionId: null,
      expiresAt: null
    });

    // Limpiar localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('token_expires_at');
    localStorage.removeItem('session_id');

    // Cancelar timer de refresh
    this.cancelTokenRefresh();
  }

  private scheduleTokenRefresh(): void {
    // Cancelar timer existente
    this.cancelTokenRefresh();

    const expiresAt = this.authState.value.expiresAt;
    if (!expiresAt) return;

    // Calcular tiempo hasta el refresh (5 minutos antes de expirar)
    const expiresIn = expiresAt.getTime() - Date.now();
    const refreshIn = Math.max(0, expiresIn - (5 * 60 * 1000)); // 5 minutos antes

    if (refreshIn > 0) {
      this.refreshTokenTimer = timer(refreshIn).pipe(
        switchMap(() => this.refreshAccessToken())
      ).subscribe({
        error: (error) => {
          console.error('Error refreshing token:', error);
          this.clearAuthState();
          this.router.navigate(['/login']);
        }
      });
    }
  }

  private cancelTokenRefresh(): void {
    if (this.refreshTokenTimer) {
      this.refreshTokenTimer.unsubscribe();
      this.refreshTokenTimer = null;
    }
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'Ha ocurrido un error';

    if (error.error instanceof ErrorEvent) {
      // Error del cliente
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Error del servidor
      if (error.status === 401) {
        errorMessage = 'Credenciales inválidas o sesión expirada';
      } else if (error.status === 403) {
        errorMessage = 'No tiene permisos para realizar esta acción';
      } else if (error.status === 422) {
        errorMessage = error.error?.detail || 'Datos inválidos';
      } else if (error.error?.detail) {
        errorMessage = error.error.detail;
      } else {
        errorMessage = `Error ${error.status}: ${error.message}`;
      }
    }

    console.error('Auth Service Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }

  // ========== GUARDS HELPERS ==========

  /**
   * Método para usar en guards de rutas
   */
  canActivate(): Observable<boolean> {
    return this.isAuthenticated$.pipe(
      map(isAuth => {
        if (!isAuth) {
          this.router.navigate(['/login']);
          return false;
        }
        return true;
      })
    );
  }

  /**
   * Método para verificar roles en guards
   */
  canActivateWithRoles(allowedRoles: string[]): Observable<boolean> {
    return this.currentUser$.pipe(
      map(user => {
        if (!user || !allowedRoles.includes(user.role)) {
          this.router.navigate(['/unauthorized']);
          return false;
        }
        return true;
      })
    );
  }
}
