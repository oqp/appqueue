// auth.interceptor.ts
import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, take, switchMap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Obtener el token
    const token = this.authService.getToken();

    // Si hay token y no es una petición de login/refresh, añadir header
    if (token && !this.isAuthEndpoint(request)) {
      request = this.addTokenToRequest(request, token);
    }

    // Procesar la petición
    return next.handle(request).pipe(
      catchError(error => {
        if (error instanceof HttpErrorResponse) {
          // Error 401: No autorizado
          if (error.status === 401 && !this.isAuthEndpoint(request)) {
            return this.handle401Error(request, next);
          }

          // Error 403: Prohibido
          if (error.status === 403) {
            this.router.navigate(['/unauthorized']);
          }

          // Error 500: Error del servidor
          if (error.status === 500) {
            console.error('Server error:', error);
          }
        }

        return throwError(() => error);
      })
    );
  }

  private addTokenToRequest(request: HttpRequest<any>, token: string): HttpRequest<any> {
    return request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return this.authService.refreshAccessToken().pipe(
        switchMap((response: any) => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(response.access_token);

          // Reintentar la petición original con el nuevo token
          return next.handle(this.addTokenToRequest(request, response.access_token));
        }),
        catchError((error) => {
          this.isRefreshing = false;

          // Si falla el refresh, redirigir al login
          this.authService.logout();
          return throwError(() => error);
        })
      );
    } else {
      // Si ya se está refrescando el token, esperar a que termine
      return this.refreshTokenSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap(token => {
          return next.handle(this.addTokenToRequest(request, token));
        })
      );
    }
  }

  private isAuthEndpoint(request: HttpRequest<any>): boolean {
    const authEndpoints = ['/login', '/refresh', '/reset-password'];
    return authEndpoints.some(endpoint => request.url.includes(endpoint));
  }
}
