// users.component.ts
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
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatBadgeModule } from '@angular/material/badge';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { Subject, takeUntil } from 'rxjs';
import { UserService, UserResponse, Role, Station } from '../../services/user.service';
import { AuthService } from '../../services/auth.service';
import { UserDialogComponent } from '../user-dialog/user-dialog.component';

@Component({
  selector: 'app-users',
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
    MatSelectModule,
    MatDialogModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatBadgeModule,
    MatCheckboxModule,
    MatMenuModule
  ],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.scss']
})
export class UsersComponent implements OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Data
  dataSource = new MatTableDataSource<UserResponse>([]);
  displayedColumns: string[] = [
    'Username',
    'FullName',
    'Email',
    'Role',
    'Station',
    'Status',
    'LastLogin',
    'Actions'
  ];

  // State
  loading = false;
  filterForm: FormGroup;
  roles: Role[] = [];
  stations: Station[] = [];

  // Stats
  totalUsers = 0;
  activeUsers = 0;
  inactiveUsers = 0;
  usersWithStation = 0;

  // User permissions
  currentUser: any;
  canCreate = false;
  canEdit = false;
  canDelete = false;
  canAssignRole = false;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.filterForm = this.fb.group({
      search: [''],
      role: [''],
      status: [''],
      onlyActive: [false]
    });
  }

  ngOnInit(): void {
    this.setupUserPermissions();
    this.loadRoles();
    this.loadStations();
    this.loadUsers();
    this.setupFilters();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========== INITIALIZATION ==========

  private setupUserPermissions(): void {
    this.currentUser = this.authService.getCurrentUser();
    const userRole = this.currentUser?.role;

    this.canCreate = ['Admin'].includes(userRole);
    this.canEdit = ['Admin', 'Supervisor'].includes(userRole);
    this.canDelete = userRole === 'Admin';
    this.canAssignRole = userRole === 'Admin';
  }

  private setupFilters(): void {
    this.filterForm.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.applyFilters();
      });
  }

  // ========== DATA LOADING ==========

  loadRoles(): void {
    this.userService.getRoles().subscribe({
      next: (roles) => {
        this.roles = roles;
      },
      error: (error) => {
        console.error('Error loading roles:', error);
      }
    });
  }

  loadStations(): void {
    this.userService.getStations().subscribe({
      next: (response: any) => {
        if (response && response.Stations) {
          this.stations = response.Stations;
        } else if (Array.isArray(response)) {
          this.stations = response;
        }
      },
      error: (error) => {
        console.error('Error loading stations:', error);
      }
    });
  }

  loadUsers(): void {
    this.loading = true;

    this.userService.getUsers({ limit: 100 }).subscribe({
      next: (response) => {
        this.dataSource.data = response.users || [];
        this.updateStatistics();

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
        this.showError('Error al cargar los usuarios');
        console.error('Error loading users:', error);
      }
    });
  }

  // ========== STATISTICS ==========

  private updateStatistics(): void {
    const users = this.dataSource.data;

    this.totalUsers = users.length;
    this.activeUsers = users.filter(u => u.IsActive).length;
    this.inactiveUsers = users.filter(u => !u.IsActive).length;
    this.usersWithStation = users.filter(u => u.StationId).length;
  }

  // ========== FILTERS ==========

  private applyFilters(): void {
    const filters = this.filterForm.value;

    this.dataSource.filterPredicate = (user: UserResponse, filter: string) => {
      const searchStr = filters.search?.toLowerCase() || '';

      const matchesSearch = !searchStr ||
        user.Username.toLowerCase().includes(searchStr) ||
        user.FullName.toLowerCase().includes(searchStr) ||
        user.Email.toLowerCase().includes(searchStr);

      const matchesRole = !filters.role || user.RoleId === filters.role;

      const matchesStatus = filters.status === '' ||
        (filters.status === 'active' && user.IsActive) ||
        (filters.status === 'inactive' && !user.IsActive);

      const matchesActive = !filters.onlyActive || user.IsActive;

      return matchesSearch && matchesRole && matchesStatus && matchesActive;
    };

    this.dataSource.filter = JSON.stringify(filters);
  }

  clearFilters(): void {
    this.filterForm.reset({
      search: '',
      role: '',
      status: '',
      onlyActive: false
    });
  }

  // ========== ACTIONS ==========

  createUser(): void {
    if (!this.canCreate) {
      this.showError('No tiene permisos para crear usuarios');
      return;
    }

    const dialogRef = this.dialog.open(UserDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data: {
        user: null,
        roles: this.roles,
        stations: this.stations,
        isEdit: false
      },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.saveUser(result);
      }
    });
  }

  editUser(user: UserResponse): void {
    if (!this.canEdit) {
      this.showError('No tiene permisos para editar usuarios');
      return;
    }

    const dialogRef = this.dialog.open(UserDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data: {
        user: user,
        roles: this.roles,
        stations: this.stations,
        isEdit: true,
        canAssignRole: this.canAssignRole
      },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updateUser(user.Id, result);
      }
    });
  }

  viewUser(user: UserResponse): void {
    const dialogRef = this.dialog.open(UserDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data: {
        user: user,
        roles: this.roles,
        stations: this.stations,
        isEdit: false,
        isViewOnly: true
      },
      disableClose: false
    });
  }

  deleteUser(user: UserResponse): void {
    if (!this.canDelete) {
      this.showError('No tiene permisos para eliminar usuarios');
      return;
    }

    if (user.Id === this.currentUser?.id) {
      this.showError('No puede eliminar su propio usuario');
      return;
    }

    if (confirm(`¿Está seguro de desactivar al usuario ${user.FullName}?`)) {
      this.userService.deleteUser(user.Id, true).subscribe({
        next: () => {
          this.showSuccess('Usuario desactivado correctamente');
          this.loadUsers();
        },
        error: (error) => {
          this.showError('Error al desactivar el usuario');
          console.error('Error deleting user:', error);
        }
      });
    }
  }

  toggleUserStatus(user: UserResponse): void {
    if (!this.canEdit) {
      this.showError('No tiene permisos para cambiar el estado');
      return;
    }

    const newStatus = !user.IsActive;
    const action = newStatus ? 'activar' : 'desactivar';

    if (confirm(`¿Está seguro de ${action} al usuario ${user.FullName}?`)) {
      this.userService.updateUser(user.Id, { IsActive: newStatus }).subscribe({
        next: () => {
          this.showSuccess(`Usuario ${newStatus ? 'activado' : 'desactivado'} correctamente`);
          this.loadUsers();
        },
        error: (error) => {
          this.showError(`Error al ${action} el usuario`);
          console.error('Error updating user:', error);
        }
      });
    }
  }

  // ========== PRIVATE METHODS ==========

  private saveUser(userData: any): void {
    this.loading = true;

    this.userService.createUser(userData).subscribe({
      next: () => {
        this.showSuccess('Usuario creado exitosamente');
        this.loadUsers();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.message || 'Error al crear el usuario');
      }
    });
  }

  private updateUser(userId: string, userData: any): void {
    this.loading = true;

    this.userService.updateUser(userId, userData).subscribe({
      next: () => {
        this.showSuccess('Usuario actualizado exitosamente');
        this.loadUsers();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.message || 'Error al actualizar el usuario');
      }
    });
  }

  // ========== UTILITIES ==========

  getRoleName(roleId: number): string {
    const role = this.roles.find(r => r.Id === roleId);
    return role?.Name || '-';
  }

  getRoleColor(roleName: string): string {
    switch (roleName?.toLowerCase()) {
      case 'admin':
        return 'warn';
      case 'supervisor':
        return 'accent';
      case 'tecnico':
        return 'primary';
      default:
        return '';
    }
  }

  formatDate(date: Date | string | undefined): string {
    if (!date) return 'Nunca';
    const d = new Date(date);
    return d.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
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
