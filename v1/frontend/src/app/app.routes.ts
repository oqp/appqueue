import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { WorkstationsComponent } from './components/workstations/workstations.component';
import { ServiceTypesComponent } from './components/service-types/service-types.component';
import { UsersComponent } from './components/users/users.component';
import { TicketGenerationComponent } from './components/ticket-generation/ticket-generation.component';
import { QueueManagementComponent } from './components/queue-management/queue-management.component';
import { LoginComponent } from './components/login/login.component';
import { UnauthorizedComponent } from './components/unauthorized/unauthorized.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'home', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'workstations', component: WorkstationsComponent },
  { path: 'servicetypes', component: ServiceTypesComponent },
  { path: 'users', component: UsersComponent },
  { path: 'tickets', component: TicketGenerationComponent },
  { path: 'queues', component: QueueManagementComponent },
  { path: 'login', component: LoginComponent },
  { path: 'unauthorized', component: UnauthorizedComponent },
  { path: '**', redirectTo: '/dashboard' }
];
