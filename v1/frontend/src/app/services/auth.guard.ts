// auth.guard.ts
import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { map, take } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';

/**
 * Guard básico de autenticación
 * Verifica si el usuario está autenticado
 */
@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    return this.authService.isAuthenticated$.pipe(
      take(1),
      map(isAuthenticated => {
        if (!isAuthenticated) {
          // Guardar la URL intentada para redirigir después del login
          localStorage.setItem('redirectUrl', state.url);
          this.router.navigate(['/login']);
          return false;
        }
        return true;
      })
    );
  }
}

// ========================================

// role.guard.ts
/**
 * Guard de autorización por roles
 * Verifica si el usuario tiene los roles permitidos
 */
@Injectable({
  providedIn: 'root'
})
export class RoleGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    // Obtener los roles permitidos desde la configuración de la ruta
    const allowedRoles = route.data['roles'] as string[];

    if (!allowedRoles || allowedRoles.length === 0) {
      return this.authService.isAuthenticated$;
    }

    return this.authService.currentUser$.pipe(
      take(1),
      map(user => {
        if (!user) {
          this.router.navigate(['/login']);
          return false;
        }

        if (!allowedRoles.includes(user.role)) {
          this.router.navigate(['/unauthorized']);
          return false;
        }

        return true;
      })
    );
  }
}

// ========================================

// admin.guard.ts
/**
 * Guard específico para administradores
 */
@Injectable({
  providedIn: 'root'
})
export class AdminGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    return this.authService.currentUser$.pipe(
      take(1),
      map(user => {
        if (!user || user.role !== 'Admin') {
          this.router.navigate(['/unauthorized']);
          return false;
        }
        return true;
      })
    );
  }
}

// ========================================

// supervisor.guard.ts
/**
 * Guard para supervisores y administradores
 */
@Injectable({
  providedIn: 'root'
})
export class SupervisorGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    return this.authService.currentUser$.pipe(
      take(1),
      map(user => {
        if (!user || !['Admin', 'Supervisor'].includes(user.role)) {
          this.router.navigate(['/unauthorized']);
          return false;
        }
        return true;
      })
    );
  }
}

// ========================================

// technician.guard.ts
/**
 * Guard para técnicos, supervisores y administradores
 */
@Injectable({
  providedIn: 'root'
})
export class TechnicianGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    return this.authService.currentUser$.pipe(
      take(1),
      map(user => {
        if (!user || !['Admin', 'Supervisor', 'Técnico', 'Enfermero', 'Doctor'].includes(user.role)) {
          this.router.navigate(['/unauthorized']);
          return false;
        }
        return true;
      })
    );
  }
}

// ========================================

// station.guard.ts
/**
 * Guard para verificar si el usuario tiene una estación asignada
 */
@Injectable({
  providedIn: 'root'
})
export class StationGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    return this.authService.currentUser$.pipe(
      take(1),
      map(user => {
        if (!user || !user.station_id) {
          this.router.navigate(['/no-station']);
          return false;
        }
        return true;
      })
    );
  }
}
