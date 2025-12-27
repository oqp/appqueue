// workstations.component.ts
import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
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
import { MatDividerModule } from '@angular/material/divider';
import { Subject, takeUntil, timer } from 'rxjs';
import { WorkstationService } from '../../services/workstation.service';
import { AuthService } from '../../services/auth.service';
import {StationDialogComponent} from '../station-dialog/station-dialog.component';
import {MatMenu, MatMenuTrigger} from '@angular/material/menu';
import {MatCheckbox} from '@angular/material/checkbox';

// Interfaces
interface Station {
  Id: number;
  Name: string;
  Code: string;
  Description?: string;
  ServiceTypeId?: number;
  ServiceTypeName?: string;
  Location?: string;
  Status: string; //'Available' | 'Busy' | 'Maintenance' | 'Offline';
  CurrentTicketId?: string;
  CurrentTicketNumber?: string;
  IsActive: boolean;
  CreatedAt: Date;
  UpdatedAt?: Date;
  AssignedUsers?: User[];
  QueueLength?: number;
}

interface User {
  Id: string;
  Username: string;
  FullName: string;
  Role?: string;
}

interface ServiceType {
  Id: number;
  Name: string;
  Code: string;
}

@Component({
  selector: 'app-workstations',
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
    MatDividerModule,
    MatMenu,
    MatMenuTrigger,
    MatCheckbox
  ],
  templateUrl: './workstations.component.html',
  styleUrls: ['./workstations.component.scss']
})
export class WorkstationsComponent implements OnInit, OnDestroy {
  // ViewChild references
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // Data
  dataSource = new MatTableDataSource<Station>([]);
  displayedColumns: string[] = [
    'Code',
    'Name',
    'ServiceType',
    'Location',
    'Status',
    'CurrentTicket',
    'QueueLength',
    'Actions'
  ];

  // State
  loading = false;
  filterForm: FormGroup;
  serviceTypes: ServiceType[] = [];
  statusOptions = ['Available', 'Busy', 'Maintenance', 'Offline'];

  // Stats
  totalStations = 0;
  activeStations = 0;
  availableStations = 0;
  busyStations = 0;

  // User permissions
  currentUser: any;
  canEdit = false;
  canDelete = false;
  canChangeStatus = false;

  // Refresh timer
  private destroy$ = new Subject<void>();
  private refreshInterval = 30000; // 30 seconds

  constructor(
    private fb: FormBuilder,
    private workstationService: WorkstationService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    // Initialize filter form
    this.filterForm = this.fb.group({
      search: [''],
      status: [''],
      serviceType: [''],
      onlyActive: [true]
    });
  }

  ngOnInit(): void {
    this.setupUserPermissions();
    this.loadServiceTypes();
    this.loadStations();
    this.setupFilters();
    this.setupAutoRefresh();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========== INITIALIZATION ==========

  private setupUserPermissions(): void {
    this.currentUser = this.authService.getCurrentUser();
    const userRole = this.currentUser?.role;

    // Permissions based on your 4 roles: Admin, Supervisor, Tecnico, Recepcionista
    this.canEdit = ['Admin', 'Supervisor'].includes(userRole);
    this.canDelete = userRole === 'Admin';
    this.canChangeStatus = ['Admin', 'Supervisor', 'Tecnico'].includes(userRole);
  }

  private setupFilters(): void {
    // Apply filters when form changes
    this.filterForm.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.applyFilters();
      });
  }

  private setupAutoRefresh(): void {
    // Auto-refresh data every 30 seconds
    timer(this.refreshInterval, this.refreshInterval)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.loadStations(false); // Silent refresh
      });
  }

  // ========== DATA LOADING ==========

  loadServiceTypes(): void {
    this.workstationService.getServiceTypes().subscribe({
      next: (response: any) => {
        console.log('Service types response:', response);

        // El backend devuelve un array con un objeto que contiene 'services'
        if (Array.isArray(response) && response.length > 0 && response[0].services) {
          this.serviceTypes = response[0].services;
        } else if (Array.isArray(response)) {
          this.serviceTypes = response;
        } else if (response && response.services) {
          this.serviceTypes = response.services;
        } else {
          this.serviceTypes = [];
        }

        console.log('Service types procesados:', this.serviceTypes);
      },
      error: (error) => {
        console.error('Error loading service types:', error);
        this.serviceTypes = [];
      }
    });
  }

  loadStations(showLoader = true): void {
    if (showLoader) {
      this.loading = true;
    }

    const filters = this.filterForm.value;

    this.workstationService.getStations(filters).subscribe({
      next: (response) => {
        if ('Stations' in response) {
          this.dataSource.data = response.Stations || response;
        }
        this.updateStatistics();

        // Set paginator and sort after data is loaded
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
        this.showError('Error al cargar las estaciones');
        console.error('Error loading stations:', error);
      }
    });
  }

  // ========== STATISTICS ==========

  private updateStatistics(): void {
    const stations = this.dataSource.data;

    this.totalStations = stations.length;
    this.activeStations = stations.filter(s => s.IsActive).length;
    this.availableStations = stations.filter(s => s.Status === 'Available' && s.IsActive).length;
    this.busyStations = stations.filter(s => s.Status === 'Busy').length;
  }

  // ========== FILTERS ==========

  private applyFilters(): void {
    const filters = this.filterForm.value;

    this.dataSource.filterPredicate = (station: Station, filter: string) => {
      const searchStr = filters.search?.toLowerCase() || '';

      // Search filter
      const matchesSearch = !searchStr ||
        station.Name.toLowerCase().includes(searchStr) ||
        station.Code.toLowerCase().includes(searchStr) ||
        station.Location?.toLowerCase().includes(searchStr) ||
        station.Description?.toLowerCase().includes(searchStr);

      // Status filter
      const matchesStatus = !filters.status || station.Status === filters.status;

      // Service type filter
      const matchesServiceType = !filters.serviceType ||
        station.ServiceTypeId === filters.serviceType;

      // Active filter
      const matchesActive = !filters.onlyActive || station.IsActive;

      return matchesSearch && matchesStatus && matchesServiceType && matchesActive;
    };

    // Trigger filter
    this.dataSource.filter = JSON.stringify(filters);
  }

  clearFilters(): void {
    this.filterForm.reset({
      search: '',
      status: '',
      serviceType: '',
      onlyActive: true
    });
  }

  // ========== ACTIONS ==========

  changeStatus(station: Station, newStatus: string): void {
    if (!this.canChangeStatus) {
      this.showError('No tiene permisos para cambiar el estado');
      return;
    }

    const oldStatus = station.Status;

    // Confirmación para estados críticos
    if (newStatus === 'Offline') {
      if (!confirm(`¿Está seguro de poner la estación ${station.Name} fuera de línea?`)) {
        return;
      }
    }

    station.Status = newStatus;

    this.workstationService.updateStationStatus(station.Id, newStatus).subscribe({
      next: () => {
        this.showSuccess(`Estado cambiado a ${this.getStatusLabel(newStatus)}`);
        this.updateStatistics();
      },
      error: (error) => {
        station.Status = oldStatus; // Rollback
        this.showError('Error al cambiar el estado');
        console.error('Error updating status:', error);
      }
    });
  }

  editStation(station: Station): void {
    if (!this.canEdit) {
      this.showError('No tiene permisos para editar');
      return;
    }

    const dialogRef = this.dialog.open(StationDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      data: {
        station: station,
        serviceTypes: this.serviceTypes,
        isEdit: true
      },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        console.log('Updating station:', result);
        this.updateStation(station.Id, result);
      }
    });
  }

  private showInfo(message: string): void {
    this.snackBar.open(message, 'OK', {
      duration: 3000,
      panelClass: ['info-snackbar']
    });
  }

  /**
   * Update station in backend
   */
  private updateStation(stationId: number, stationData: any): void {
    this.loading = true;

    this.workstationService.updateStation(stationId, stationData).subscribe({
      next: (response) => {
        this.showSuccess('Estación actualizada exitosamente');
        this.loadStations(); // Reload list
      },
      error: (error) => {
        this.loading = false;
        console.error('Error updating station:', error);
        this.showError(error.message || 'Error al actualizar la estación');
      }
    });
  }

  deleteStation(station: Station): void {
    if (!this.canDelete) {
      this.showError('No tiene permisos para eliminar');
      return;
    }

    if (confirm(`¿Está seguro de eliminar la estación ${station.Name}?`)) {
      this.workstationService.deleteStation(station.Id).subscribe({
        next: () => {
          this.showSuccess('Estación eliminada correctamente');
          this.loadStations();
        },
        error: (error) => {
          this.showError('Error al eliminar la estación');
          console.error('Error deleting station:', error);
        }
      });
    }
  }

  viewDetails(station: Station): void {

    if (!this.canEdit) {
      this.showError('No tiene permisos para editar');
      return;
    }

    const dialogRef = this.dialog.open(StationDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      data: {
        station: station,
        serviceTypes: this.serviceTypes,
        isEdit: true,
        isViewOnly: true
      },
      disableClose: true
    });


  }

  assignUser(station: Station): void {
    if (!this.canEdit) {
      this.showError('No tiene permisos para asignar usuarios');
      return;
    }

    // TODO: Open assign user dialog
    console.log('Assign user to station:', station);
  }

  // ========== UTILITIES ==========

  getStatusColor(status: string): string {
    switch (status) {
      case 'Available':
        return 'primary';
      case 'Busy':
        return 'accent';
      case 'Maintenance':
        return 'warn';
      case 'Offline':
        return '';
      default:
        return '';
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'Available':
        return 'check_circle';
      case 'Busy':
        return 'pending';
      case 'Maintenance':
        return 'build';
      case 'Offline':
        return 'cancel';
      default:
        return 'help';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'Available':
        return 'Disponible';
      case 'Busy':
        return 'Ocupado';
      case 'Maintenance':
        return 'Mantenimiento';
      case 'Offline':
        return 'Fuera de línea';
      default:
        return status;
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

  createStation(): void {
    // Si no hay serviceTypes, cargarlos primero
    if (!this.serviceTypes || this.serviceTypes.length === 0) {
      this.workstationService.getServiceTypes().subscribe({
        next: (response: any) => {
          // Procesar response como array
          if (Array.isArray(response)) {
            this.serviceTypes = response;
          } else {
            this.serviceTypes = [];
          }

          // Ahora sí abrir el diálogo
          this.openStationDialog();
        },
        error: (error) => {
          console.error('Error loading service types:', error);
          this.showError('Error al cargar tipos de servicio');
        }
      });
    } else {
      this.openStationDialog();
    }
  }

  private openStationDialog(): void {
    const dialogRef = this.dialog.open(StationDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      data: {
        station: null,
        serviceTypes: this.serviceTypes,
        isEdit: false
      },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        console.log('Creating station:', result);
        this.saveStation(result);
      }
    });
  }

  /**
   * Save new station to backend
   */
  private saveStation(stationData: any): void {
    this.loading = true;

    this.workstationService.createStation(stationData).subscribe({
      next: (response) => {
        this.loading = false;
        this.showSuccess('Estación creada exitosamente');
        this.loadStations(); // Reload list
      },
      error: (error) => {
        this.loading = false;
        console.error('Error creating station:', error);
        this.showError(error.message || 'Error al crear la estación');
      }
    });
  }


}
