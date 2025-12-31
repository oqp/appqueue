// roles.component.ts
import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatBadgeModule } from '@angular/material/badge';
import { Subject, takeUntil } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environments';
import { AuthService } from '../../services/auth.service';
import { RoleDialogComponent } from '../role-dialog/role-dialog.component';

interface Role {
  Id: number;
  Name: string;
  Description: string;
  IsActive: boolean;
  Permissions?: string[];
  UserCount?: number;
  CreatedAt?: string;
  UpdatedAt?: string;
}

@Component({
  selector: 'app-roles',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatBadgeModule
  ],
  templateUrl: './roles.component.html',
  styleUrls: ['./roles.component.scss']
})
export class RolesComponent implements OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Data
  dataSource = new MatTableDataSource<Role>([]);
  displayedColumns: string[] = ['Id', 'Name', 'Description', 'UserCount', 'Status', 'Actions'];

  // State
  loading = false;
  searchTerm = '';

  // Stats
  totalRoles = 0;
  activeRoles = 0;
  totalUsersAssigned = 0;

  // Permissions
  canCreate = false;
  canEdit = false;
  canDelete = false;

  private destroy$ = new Subject<void>();
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.setupPermissions();
    this.loadRoles();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupPermissions(): void {
    const currentUser = this.authService.getCurrentUser();
    const userRole = currentUser?.role;

    this.canCreate = userRole === 'Admin';
    this.canEdit = userRole === 'Admin';
    this.canDelete = userRole === 'Admin';
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  loadRoles(): void {
    this.loading = true;

    this.http.get<Role[]>(`${this.apiUrl}/admin/roles`, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (roles) => {
        this.dataSource.data = roles;
        this.updateStatistics(roles);

        if (this.paginator) {
          this.dataSource.paginator = this.paginator;
        }
        if (this.sort) {
          this.dataSource.sort = this.sort;
        }

        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.showError('Error al cargar los roles');
        console.error('Error loading roles:', error);
      }
    });
  }

  private updateStatistics(roles: Role[]): void {
    this.totalRoles = roles.length;
    this.activeRoles = roles.filter(r => r.IsActive).length;
    this.totalUsersAssigned = roles.reduce((sum, r) => sum + (r.UserCount || 0), 0);
  }

  applyFilter(): void {
    this.dataSource.filter = this.searchTerm.trim().toLowerCase();
  }

  clearSearch(): void {
    this.searchTerm = '';
    this.applyFilter();
  }

  // ========== ACTIONS ==========

  createRole(): void {
    if (!this.canCreate) {
      this.showError('No tiene permisos para crear roles');
      return;
    }

    const dialogRef = this.dialog.open(RoleDialogComponent, {
      width: '500px',
      maxWidth: '95vw',
      data: {
        role: null,
        isEdit: false
      },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.saveRole(result);
      }
    });
  }

  editRole(role: Role): void {
    if (!this.canEdit) {
      this.showError('No tiene permisos para editar roles');
      return;
    }

    // Obtener detalles completos del rol
    this.http.get<Role>(`${this.apiUrl}/admin/roles/${role.Id}`, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (fullRole) => {
        const dialogRef = this.dialog.open(RoleDialogComponent, {
          width: '500px',
          maxWidth: '95vw',
          data: {
            role: fullRole,
            isEdit: true
          },
          disableClose: true
        });

        dialogRef.afterClosed().subscribe(result => {
          if (result) {
            this.updateRole(role.Id, result);
          }
        });
      },
      error: (error) => {
        this.showError('Error al cargar los detalles del rol');
        console.error('Error loading role details:', error);
      }
    });
  }

  viewRole(role: Role): void {
    this.http.get<Role>(`${this.apiUrl}/admin/roles/${role.Id}`, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (fullRole) => {
        this.dialog.open(RoleDialogComponent, {
          width: '500px',
          maxWidth: '95vw',
          data: {
            role: fullRole,
            isEdit: false,
            isViewOnly: true
          },
          disableClose: false
        });
      },
      error: (error) => {
        this.showError('Error al cargar los detalles del rol');
        console.error('Error loading role details:', error);
      }
    });
  }

  deleteRole(role: Role): void {
    if (!this.canDelete) {
      this.showError('No tiene permisos para eliminar roles');
      return;
    }

    if (role.UserCount && role.UserCount > 0) {
      this.showError(`No se puede eliminar el rol "${role.Name}" porque tiene ${role.UserCount} usuario(s) asignado(s)`);
      return;
    }

    if (confirm(`¿Está seguro de eliminar el rol "${role.Name}"?`)) {
      this.http.delete(`${this.apiUrl}/admin/roles/${role.Id}`, {
        headers: this.getAuthHeaders()
      }).subscribe({
        next: () => {
          this.showSuccess('Rol eliminado correctamente');
          this.loadRoles();
        },
        error: (error) => {
          this.showError('Error al eliminar el rol');
          console.error('Error deleting role:', error);
        }
      });
    }
  }

  initDefaultRoles(): void {
    if (!this.canCreate) {
      this.showError('No tiene permisos para inicializar roles');
      return;
    }

    if (confirm('¿Desea crear los roles por defecto del sistema (Admin, Supervisor, Técnico, Recepcionista)?')) {
      this.loading = true;

      this.http.post<any>(`${this.apiUrl}/admin/roles/init`, {}, {
        headers: this.getAuthHeaders()
      }).subscribe({
        next: (response) => {
          if (response.created && response.created.length > 0) {
            this.showSuccess(`Roles creados: ${response.created.join(', ')}`);
          } else {
            this.showSuccess('Todos los roles ya existen');
          }
          this.loadRoles();
        },
        error: (error) => {
          this.loading = false;
          this.showError('Error al inicializar roles');
          console.error('Error initializing roles:', error);
        }
      });
    }
  }

  // ========== PRIVATE METHODS ==========

  private saveRole(roleData: any): void {
    this.loading = true;

    this.http.post<Role>(`${this.apiUrl}/admin/roles`, roleData, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.showSuccess('Rol creado exitosamente');
        this.loadRoles();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.error?.detail || 'Error al crear el rol');
      }
    });
  }

  private updateRole(roleId: number, roleData: any): void {
    this.loading = true;

    this.http.put<Role>(`${this.apiUrl}/admin/roles/${roleId}`, roleData, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.showSuccess('Rol actualizado exitosamente');
        this.loadRoles();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.error?.detail || 'Error al actualizar el rol');
      }
    });
  }

  // ========== UTILITIES ==========

  getRoleColor(roleName: string): string {
    switch (roleName?.toLowerCase()) {
      case 'admin':
        return '#d32f2f';
      case 'supervisor':
        return '#f57c00';
      case 'tecnico':
        return '#1976d2';
      case 'recepcionista':
        return '#388e3c';
      default:
        return '#616161';
    }
  }

  getRoleIcon(roleName: string): string {
    switch (roleName?.toLowerCase()) {
      case 'admin':
        return 'admin_panel_settings';
      case 'supervisor':
        return 'supervisor_account';
      case 'tecnico':
        return 'biotech';
      case 'recepcionista':
        return 'desk';
      default:
        return 'person';
    }
  }

  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 3000,
      panelClass: ['success-snackbar']
    });
  }

  private showError(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 5000,
      panelClass: ['error-snackbar']
    });
  }
}
