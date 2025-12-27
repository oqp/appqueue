import { bootstrapApplication } from '@angular/platform-browser';
import { importProvidersFrom } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import {provideRouter, Routes} from '@angular/router';

import { AppComponent } from './app/app.component';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {DashboardComponent} from './app/components/dashboard/dashboard.component';



// Services
import { MenuService } from './app/menu.service';

// Routes configuration with guards
const routes: Routes = [
  // Rutas públicas
  { path: 'login', component: LoginComponent },
  { path: 'unauthorized', component: UnauthorizedComponent },

  // Rutas protegidas
  {
    path: '',
    canActivate: [AuthGuard],
    children: [
      { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
      { path: 'home', component: AppComponent },
      { path: 'dashboard', component: DashboardComponent },

      // Rutas con permisos específicos
      {
        path: 'workstations',
        component: WorkstationsComponent,
        canActivate: [RoleGuard],
        data: { roles: ['Admin', 'Supervisor', 'Técnico', 'Enfermero', 'Doctor'] }
      },
      {
        path: 'servicetypes',
        component: ServiceTypesComponent,
        canActivate: [RoleGuard],
        data: { roles: ['Admin', 'Supervisor'] }
      },
      {
        path: 'patients',
        component: AppComponent,
        canActivate: [RoleGuard],
        data: { roles: ['Admin', 'Supervisor', 'Técnico', 'Enfermero', 'Doctor', 'Recepcionista'] }
      },

      {
        path: 'tickets',
        component: TicketGenerationComponent,
        canActivate: [AuthGuard] // Todos los usuarios autenticados
      },

      {
        path: 'queues',
        component: QueueManagementComponent,
        canActivate: [AuthGuard]
      },

      {
        path: 'users',
        component: AppComponent,
        canActivate: [AdminGuard] // Solo administradores
      },

      {
        path: 'reports',
        component: AppComponent,
        canActivate: [SupervisorGuard] // Supervisores y administradores
      },

      {
        path: 'notifications',
        component: AppComponent,
        canActivate: [AuthGuard]
      },

      {
        path: 'websocket',
        component: AppComponent,
        canActivate: [AuthGuard]
      }
    ]
  },

  // Wildcard route
  { path: '**', redirectTo: '/dashboard' }
];

// Bootstrap application with authentication
bootstrapApplication(AppComponent, {
  providers: [
    // Browser animations
    importProvidersFrom(BrowserAnimationsModule),

    // Router with guards
    provideRouter(routes),

    // HTTP Client with interceptor
    provideHttpClient(),
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },

    // Services
    MenuService,
    AuthService,
    WorkstationService,

    // Guards
    AuthGuard,
    RoleGuard,
    AdminGuard,
    SupervisorGuard,

    // Angular Material animations
    provideAnimationsAsync(), provideAnimationsAsync()
  ]
}).catch(err => console.error('Error starting application:', err));


// Services
import { AuthService } from './app/services/auth.service';
import { WorkstationService } from './app/services/workstation.service';
import {HTTP_INTERCEPTORS, provideHttpClient} from '@angular/common/http';
import {AdminGuard, AuthGuard, RoleGuard, SupervisorGuard} from './app/services/auth.guard';
import {WorkstationsComponent} from './app/components/workstations/workstations.component';
import {AuthInterceptor} from './app/services/auth.interceptor';
import {LoginComponent} from './app/components/login/login.component';
import {UnauthorizedComponent} from './app/components/unauthorized/unauthorized.component';
import {ServiceTypesComponent} from './app/components/service-types/service-types.component';
import {TicketGenerationComponent} from './app/components/ticket-generation/ticket-generation.component';
import {QueueManagementComponent} from './app/components/queue-management/queue-management.component';
//
//
// // Basic routes configuration
// const routes: Routes = [
//   { path: '', redirectTo: '/home', pathMatch: 'full' },
//   { path: 'home', component: AppComponent },
//   { path: 'dashboard', component: DashboardComponent },
//   { path: 'patients', component: AppComponent },
//   { path: 'tickets', component: AppComponent },
//   { path: 'queues', component: AppComponent },
//   { path: 'workstations', component: AppComponent },
//   { path: 'users', component: AppComponent },
//   { path: 'reports', component: AppComponent },
//   { path: 'notifications', component: AppComponent },
//   { path: 'websocket', component: AppComponent },
//   { path: '**', redirectTo: '/home' } // Wildcard route
// ];
//
// bootstrapApplication(AppComponent, {
//   providers: [
//     // Browser animations
//     importProvidersFrom(BrowserAnimationsModule),
//
//     // Router
//     provideRouter(routes),
//
//     // Services
//     MenuService, provideAnimationsAsync()
//   ]
// }).catch(err => console.error('Error starting application:', err));
