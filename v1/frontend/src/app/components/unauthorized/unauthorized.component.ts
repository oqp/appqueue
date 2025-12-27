// unauthorized.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Location } from '@angular/common';
import { Subject, takeUntil, interval } from 'rxjs';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';

// Services
import { AuthService } from '../../services/auth.service';

interface AccessRequirement {
  icon: string;
  title: string;
  description: string;
  roles: string[];
}

interface CommonRoute {
  path: string;
  label: string;
  icon: string;
  description: string;
  requiredRoles: string[];
}

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatListModule,
    MatExpansionModule,
    MatTooltipModule,
    MatProgressBarModule
  ],
  templateUrl: './unauthorized.component.html',
  styleUrls: ['./unauthorized.component.scss']
})
export class UnauthorizedComponent implements OnInit, OnDestroy {
  // User information
  currentUser: any = null;
  userRole: string = '';
  userName: string = '';

  // Navigation
  attemptedUrl: string = '';
  redirectCountdown: number = 10;
  autoRedirectEnabled: boolean = true;

  // Animation states
  cardAnimation: string = '';
  iconAnimation: string = '';

  // Common routes based on role
  availableRoutes: CommonRoute[] = [];
  restrictedRoutes: CommonRoute[] = [];

  // Access requirements
  accessRequirements: AccessRequirement[] = [
    {
      icon: 'admin_panel_settings',
      title: 'Acceso de Administrador',
      description: 'Gestión completa del sistema, usuarios y configuraciones',
      roles: ['Admin']
    },
    {
      icon: 'supervisor_account',
      title: 'Acceso de Supervisor',
      description: 'Gestión de operaciones, reportes y supervisión de personal',
      roles: ['Admin', 'Supervisor']
    },
    {
      icon: 'medical_services',
      title: 'Acceso Médico',
      description: 'Gestión de pacientes, resultados y servicios médicos',
      roles: ['Admin', 'Supervisor', 'Doctor', 'Enfermero', 'Técnico']
    },
    {
      icon: 'desk',
      title: 'Acceso de Recepción',
      description: 'Registro de pacientes y gestión de tickets',
      roles: ['Admin', 'Supervisor', 'Recepcionista']
    }
  ];

  // All system routes - Updated for your 4 roles
  private systemRoutes: CommonRoute[] = [
    {
      path: '/dashboard',
      label: 'Dashboard',
      icon: 'dashboard',
      description: 'Panel principal con estadísticas',
      requiredRoles: []
    },
    {
      path: '/patients',
      label: 'Gestión de Pacientes',
      icon: 'people',
      description: 'Registro y gestión de pacientes',
      requiredRoles: ['Admin', 'Supervisor', 'Tecnico', 'Recepcionista']
    },
    {
      path: '/tickets',
      label: 'Tickets',
      icon: 'confirmation_number',
      description: 'Gestión de tickets y turnos',
      requiredRoles: []
    },
    {
      path: '/queues',
      label: 'Colas',
      icon: 'queue',
      description: 'Monitoreo de colas en tiempo real',
      requiredRoles: []
    },
    {
      path: '/workstations',
      label: 'Estaciones de Trabajo',
      icon: 'desktop_windows',
      description: 'Gestión de ventanillas y estaciones',
      requiredRoles: ['Admin', 'Supervisor', 'Tecnico']
    },
    {
      path: '/users',
      label: 'Usuarios',
      icon: 'group',
      description: 'Administración de usuarios del sistema',
      requiredRoles: ['Admin']
    },
    {
      path: '/reports',
      label: 'Reportes',
      icon: 'assessment',
      description: 'Reportes y análisis estadísticos',
      requiredRoles: ['Admin', 'Supervisor']
    },
    {
      path: '/notifications',
      label: 'Notificaciones',
      icon: 'notifications',
      description: 'Centro de notificaciones',
      requiredRoles: []
    },
    {
      path: '/settings',
      label: 'Configuración',
      icon: 'settings',
      description: 'Configuración del sistema',
      requiredRoles: ['Admin']
    }
  ];

  // Support information
  supportEmail: string = 'soporte@laboratorio.com';
  supportPhone: string = '+1 234-567-8900';
  supportHours: string = 'Lunes a Viernes, 8:00 AM - 6:00 PM';

  // Cleanup
  private destroy$ = new Subject<void>();
  private redirectTimer: any;

  constructor(
    private router: Router,
    private location: Location,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    // Get current user information
    this.loadUserInfo();

    // Get attempted URL
    this.attemptedUrl = this.location.path() || '';

    // Categorize routes based on user role
    this.categorizeRoutes();

    // Start animations
    this.startAnimations();

    // Start auto-redirect countdown
    if (this.autoRedirectEnabled) {
      this.startRedirectCountdown();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    if (this.redirectTimer) {
      clearInterval(this.redirectTimer);
    }
  }

  // ========== USER INFORMATION ==========

  private loadUserInfo(): void {
    this.currentUser = this.authService.getCurrentUser();

    if (this.currentUser) {
      this.userRole = this.currentUser.role || 'Sin Rol';
      this.userName = this.currentUser.full_name || this.currentUser.username || 'Usuario';
    } else {
      this.userRole = 'No Autenticado';
      this.userName = 'Invitado';
    }
  }

  // ========== ROUTE CATEGORIZATION ==========

  private categorizeRoutes(): void {
    if (!this.currentUser) {
      this.restrictedRoutes = this.systemRoutes;
      this.availableRoutes = [];
      return;
    }

    this.systemRoutes.forEach(route => {
      if (this.canAccessRoute(route)) {
        this.availableRoutes.push(route);
      } else {
        this.restrictedRoutes.push(route);
      }
    });
  }

  private canAccessRoute(route: CommonRoute): boolean {
    // If no roles required, everyone can access
    if (!route.requiredRoles || route.requiredRoles.length === 0) {
      return true;
    }

    // Check if user has required role
    return this.currentUser && route.requiredRoles.includes(this.currentUser.role);
  }

  // ========== ANIMATIONS ==========

  private startAnimations(): void {
    setTimeout(() => {
      this.cardAnimation = 'card-slide-in';
      this.iconAnimation = 'icon-pulse';
    }, 100);
  }

  // ========== NAVIGATION ==========

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }

  goBack(): void {
    // Try to go back in history
    this.location.back();
  }

  goHome(): void {
    if (this.currentUser) {
      this.router.navigate(['/dashboard']);
    } else {
      this.router.navigate(['/login']);
    }
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/login']);
      },
      error: (error) => {
        console.error('Error during logout:', error);
        // Force navigation even if logout fails
        this.router.navigate(['/login']);
      }
    });
  }

  // ========== AUTO-REDIRECT ==========

  private startRedirectCountdown(): void {
    this.redirectTimer = interval(1000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.redirectCountdown--;

        if (this.redirectCountdown <= 0) {
          this.goHome();
        }
      });
  }

  cancelAutoRedirect(): void {
    this.autoRedirectEnabled = false;
    if (this.redirectTimer) {
      this.redirectTimer.unsubscribe();
    }
  }

  // ========== HELPERS ==========

  getRoleColor(role: string): string {
    const roleColors: { [key: string]: string } = {
      'Admin': '#e91e63',
      'Supervisor': '#9c27b0',
      'Doctor': '#2196f3',
      'Enfermero': '#00bcd4',
      'Técnico': '#4caf50',
      'Recepcionista': '#ff9800',
      'No Autenticado': '#757575'
    };

    return roleColors[role] || '#607d8b';
  }

  getRoleIcon(role: string): string {
    const roleIcons: { [key: string]: string } = {
      'Admin': 'admin_panel_settings',
      'Supervisor': 'supervisor_account',
      'Doctor': 'medical_services',
      'Enfermero': 'local_hospital',
      'Técnico': 'biotech',
      'Recepcionista': 'desk',
      'No Autenticado': 'person_off'
    };

    return roleIcons[role] || 'person';
  }

  getRouteRequirementsText(route: CommonRoute): string {
    if (!route.requiredRoles || route.requiredRoles.length === 0) {
      return 'Acceso general';
    }

    if (route.requiredRoles.length === 1) {
      return `Solo ${route.requiredRoles[0]}`;
    }

    return route.requiredRoles.join(', ');
  }

  isAccessible(requirement: AccessRequirement): boolean {
    return this.currentUser && requirement.roles.includes(this.currentUser.role);
  }

  // ========== CONTACT SUPPORT ==========

  contactSupport(): void {
    window.location.href = `mailto:${this.supportEmail}?subject=Solicitud de Acceso - ${this.userName}`;
  }

  copyEmail(): void {
    navigator.clipboard.writeText(this.supportEmail).then(() => {
      // You could add a snackbar notification here
      console.log('Email copiado al portapapeles');
    });
  }
}
