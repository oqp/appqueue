// queue-management.component.ts
import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { Subject, takeUntil, interval, timer } from 'rxjs';

// Angular Material Modules
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatMenuModule } from '@angular/material/menu';

// Services
import { QueueService } from '../../services/queue.service';
import { AuthService } from '../../services/auth.service';

// Interfaces
interface QueueState {
  Id: number;
  ServiceTypeId: number;
  ServiceName?: string;
  ServiceCode?: string;
  StationId?: number;
  StationName?: string;
  StationCode?: string;
  CurrentTicketId?: string;
  CurrentTicketNumber?: string;
  NextTicketId?: string;
  NextTicketNumber?: string;
  QueueLength: number;
  AverageWaitTime: number;
  LastUpdateAt: Date;
  IsActive: boolean;
  EstimatedWaitTime?: number;
  Color?: string;
  TicketPrefix?: string;
  PendingTickets?: Ticket[];
}

interface QueueSummary {
  TotalQueues: number;
  ActiveQueues: number;
  TotalWaiting: number;
  StationsBusy: number;
  AverageWaitTime: number;
}

interface Ticket {
  Id: string;
  TicketNumber: string;
  PatientName: string;
  Position: number;
  EstimatedTime?: Date;
  Status: string;
}

interface ServiceType {
  Id: number;
  Name: string;
  Code: string;
  Color: string;
  TicketPrefix: string;
}

@Component({
  selector: 'app-queue-management',
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
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatBadgeModule,
    MatDividerModule,
    MatDialogModule,
    MatTabsModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatMenuModule
  ],
  templateUrl: './queue-management.component.html',
  styleUrls: ['./queue-management.component.scss']
})
export class QueueManagementComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // ViewChild references
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  // State
  isLoading = false;
  autoRefresh = true;
  refreshInterval = 10000; // 10 seconds
  selectedTab = 0;

  // Queue Data
  queueStates: QueueState[] = [];
  activeQueues: QueueState[] = [];
  summary: QueueSummary = {
    TotalQueues: 0,
    ActiveQueues: 0,
    TotalWaiting: 0,
    StationsBusy: 0,
    AverageWaitTime: 0
  };

  // Table
  displayedColumns: string[] = [
    'service',
    'station',
    'currentTicket',
    'queueLength',
    'avgWaitTime',
    'status',
    'actions'
  ];
  dataSource = new MatTableDataSource<QueueState>([]);

  // Filters
  filterForm: FormGroup;
  serviceTypes: ServiceType[] = [];
  selectedServiceType: number | null = null;
  selectedStation: number | null = null;
  showActiveOnly = true;

  // User permissions
  canManageQueues = false;
  currentUser: any = null;

  constructor(
    private fb: FormBuilder,
    private queueService: QueueService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.filterForm = this.fb.group({
      searchText: [''],
      serviceTypeId: [null],
      stationId: [null],
      showActiveOnly: [true]
    });
  }

  ngOnInit(): void {
    this.checkPermissions();
    this.loadInitialData();
    this.setupAutoRefresh();
    this.setupFilters();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // Permissions
  private checkPermissions(): void {
    this.currentUser = this.authService.getCurrentUser();
    const userRole = this.currentUser?.role;
    this.canManageQueues = ['admin', 'supervisor', 'technician'].includes(userRole?.toLowerCase());
  }

  // Data Loading
  private loadInitialData(): void {
    this.initializeAndLoadQueues();
    this.loadServiceTypes();
  }

  private initializeAndLoadQueues(): void {
    this.isLoading = true;

    // Primero intentar inicializar las colas
    this.queueService.initializeAllQueues()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          console.log('Inicialización:', result);
          if (result.success || result.details) {
            this.showMessage(
              `Inicialización: ${result.details?.queues_created || 0} colas creadas, ${result.details?.queues_updated || 0} actualizadas`,
              'success'
            );
          }
          // Después de inicializar, cargar los datos
          this.loadQueueStates();
          this.loadSummary();
        },
        error: (error) => {
          console.error('Error en inicialización:', error);
          // Si falla la inicialización, intentar cargar de todos modos
          this.loadQueueStates();
          this.loadSummary();
        }
      });
  }

  loadQueueStates(): void {
    this.isLoading = true;

    this.queueService.getQueueStates(this.showActiveOnly)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (states) => {
          console.log('Estados de cola cargados:', states);
          this.queueStates = states;
          this.activeQueues = states.filter(q => q.IsActive && q.QueueLength > 0);
          this.updateDataSource();
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading queue states:', error);
          this.showMessage('Error al cargar estados de cola', 'error');
          this.isLoading = false;
        }
      });
  }

  // Método para el botón Actualizar
  refreshData(): void {
    this.isLoading = true;

    // Usar refresh-all para recalcular todo
    this.queueService.refreshAllQueues()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          console.log('Refresh completado:', result);
          this.showMessage(result.message || 'Datos actualizados', 'success');
          this.loadQueueStates();
          this.loadSummary();
        },
        error: (error) => {
          console.error('Error en refresh:', error);
          // Si falla, intentar solo recargar
          this.loadQueueStates();
          this.loadSummary();
        }
      });
  }

  loadSummary(): void {
    this.queueService.getQueueSummary()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (summary) => {
          this.summary = summary;
        },
        error: (error) => {
          console.error('Error loading summary:', error);
        }
      });
  }

  loadServiceTypes(): void {
    this.queueService.getServiceTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (types) => {
          this.serviceTypes = types;
        },
        error: (error) => {
          console.error('Error loading service types:', error);
        }
      });
  }

  // Table Management
  private updateDataSource(): void {
    let filteredData = [...this.queueStates];

    // Apply filters
    const filters = this.filterForm.value;

    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      filteredData = filteredData.filter(q =>
        q.ServiceName?.toLowerCase().includes(searchLower) ||
        q.StationName?.toLowerCase().includes(searchLower) ||
        q.CurrentTicketNumber?.toLowerCase().includes(searchLower)
      );
    }

    if (filters.serviceTypeId) {
      filteredData = filteredData.filter(q => q.ServiceTypeId === filters.serviceTypeId);
    }

    if (filters.stationId) {
      filteredData = filteredData.filter(q => q.StationId === filters.stationId);
    }

    if (filters.showActiveOnly) {
      filteredData = filteredData.filter(q => q.IsActive);
    }

    this.dataSource.data = filteredData;

    if (this.paginator) {
      this.dataSource.paginator = this.paginator;
    }
    if (this.sort) {
      this.dataSource.sort = this.sort;
    }
  }

  // Auto Refresh
  private setupAutoRefresh(): void {
    interval(this.refreshInterval)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        if (this.autoRefresh && !this.isLoading) {
          this.loadQueueStates();
          this.loadSummary();
        }
      });
  }

  toggleAutoRefresh(): void {
    this.autoRefresh = !this.autoRefresh;
    const message = this.autoRefresh ?
      'Auto-actualización activada' :
      'Auto-actualización desactivada';
    this.showMessage(message, 'info');
  }

  // Filters
  private setupFilters(): void {
    this.filterForm.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.updateDataSource();
      });
  }

  clearFilters(): void {
    this.filterForm.reset({
      searchText: '',
      serviceTypeId: null,
      stationId: null,
      showActiveOnly: true
    });
  }

  // Queue Operations
  advanceQueue(queue: QueueState): void {
    if (!this.canManageQueues) {
      this.showMessage('No tiene permisos para esta acción', 'warning');
      return;
    }

    const confirmMessage = queue.CurrentTicketNumber ?
      `¿Avanzar cola del servicio ${queue.ServiceName}? Ticket actual: ${queue.CurrentTicketNumber}` :
      `¿Comenzar a atender cola del servicio ${queue.ServiceName}?`;

    if (!confirm(confirmMessage)) {
      return;
    }

    this.isLoading = true;

    this.queueService.advanceQueue(queue.ServiceTypeId, queue.StationId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.showMessage('Cola avanzada correctamente', 'success');
          this.loadQueueStates();
          this.loadSummary();
        },
        error: (error) => {
          console.error('Error advancing queue:', error);
          this.showMessage('Error al avanzar la cola', 'error');
          this.isLoading = false;
        }
      });
  }

  resetQueue(queue: QueueState): void {
    if (!this.canManageQueues) {
      this.showMessage('No tiene permisos para esta acción', 'warning');
      return;
    }

    const confirmMessage = `¿Está seguro de reiniciar la cola del servicio ${queue.ServiceName}?
                           Esta acción no se puede deshacer.`;

    if (!confirm(confirmMessage)) {
      return;
    }

    const reason = prompt('Ingrese el motivo del reinicio:');
    if (!reason) {
      return;
    }

    this.isLoading = true;

    this.queueService.resetQueue(queue.ServiceTypeId, queue.StationId, reason)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.showMessage('Cola reiniciada correctamente', 'success');
          this.loadQueueStates();
          this.loadSummary();
        },
        error: (error) => {
          console.error('Error resetting queue:', error);
          this.showMessage('Error al reiniciar la cola', 'error');
          this.isLoading = false;
        }
      });
  }

  updateWaitTime(queue: QueueState): void {
    if (!this.canManageQueues) {
      this.showMessage('No tiene permisos para esta acción', 'warning');
      return;
    }

    const newTime = prompt('Ingrese el nuevo tiempo de espera (minutos):',
      queue.AverageWaitTime.toString());

    if (!newTime || isNaN(Number(newTime))) {
      return;
    }

    this.isLoading = true;

    this.queueService.updateWaitTime(queue.Id, Number(newTime))
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.showMessage('Tiempo de espera actualizado', 'success');
          this.loadQueueStates();
        },
        error: (error) => {
          console.error('Error updating wait time:', error);
          this.showMessage('Error al actualizar tiempo de espera', 'error');
          this.isLoading = false;
        }
      });
  }

  viewQueueDetails(queue: QueueState): void {
    // Importar dinámicamente el componente del diálogo
    import('../queue-details-dialog/queue-details-dialog.component').then(module => {
      const dialogRef = this.dialog.open(module.QueueDetailsDialogComponent, {
        width: '900px',
        maxWidth: '90vw',
        maxHeight: '70vh',
        panelClass: 'full-width',
        data: {
          queue: queue,
          tickets: [],
          statistics: null
        }
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result === 'refresh') {
          this.loadQueueStates();
        }
      });
    });
  }

  // UI Helpers
  getStatusColor(queue: QueueState): string {
    if (!queue.IsActive) return '#f5f5f5';      // Gris muy claro
    if (queue.QueueLength === 0) return '#e8f5e9';  // Verde muy claro
    if (queue.QueueLength <= 5) return '#e3f2fd';   // Azul muy claro
    if (queue.QueueLength <= 10) return '#fff3e0';  // Naranja muy claro
    return '#ffebee';  // Rojo muy claro
  }

  getStatusTextColor(queue: QueueState): string {
    // Texto blanco para todos los estados para mejor legibilidad
    return 'white';
  }

  getStatusIcon(queue: QueueState): string {
    if (!queue.IsActive) return 'block';
    if (queue.QueueLength === 0) return 'check_circle';
    if (queue.QueueLength <= 5) return 'schedule';
    if (queue.QueueLength <= 10) return 'warning';
    return 'error';
  }

  getStatusLabel(queue: QueueState): string {
    if (!queue.IsActive) return 'Inactiva';
    if (queue.QueueLength === 0) return 'Sin espera';
    if (queue.QueueLength <= 5) return 'Espera corta';
    if (queue.QueueLength <= 10) return 'Espera moderada';
    return 'Espera larga';
  }

  formatWaitTime(minutes: number): string {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  }

  // Messages
  private showMessage(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    const panelClass = type === 'error' ? 'error-snackbar' :
      type === 'warning' ? 'warning-snackbar' :
        type === 'info' ? 'info-snackbar' : 'success-snackbar';

    this.snackBar.open(message, 'Cerrar', {
      duration: 4000,
      horizontalPosition: 'end',
      verticalPosition: 'bottom',
      panelClass: [panelClass]
    });
  }

  // Statistics Helper Methods
  getQueueCountByService(serviceId: number): number {
    return this.queueStates
      .filter(q => q.ServiceTypeId === serviceId && q.IsActive)
      .reduce((sum, q) => sum + q.QueueLength, 0);
  }

  getServiceLoadPercentage(serviceId: number): number {
    const queueCount = this.getQueueCountByService(serviceId);
    const maxExpected = 20; // Maximum expected queue size
    return Math.min((queueCount / maxExpected) * 100, 100);
  }

  getMinWaitTime(): string {
    if (this.queueStates.length === 0) return '0 min';

    const activeQueues = this.queueStates.filter(q => q.IsActive && q.QueueLength > 0);
    if (activeQueues.length === 0) return '0 min';

    const minTime = Math.min(...activeQueues.map(q => q.AverageWaitTime));
    return this.formatWaitTime(minTime);
  }

  getMaxWaitTime(): string {
    if (this.queueStates.length === 0) return '0 min';

    const activeQueues = this.queueStates.filter(q => q.IsActive && q.QueueLength > 0);
    if (activeQueues.length === 0) return '0 min';

    const maxTime = Math.max(...activeQueues.map(q => q.AverageWaitTime));
    return this.formatWaitTime(maxTime);
  }

  // Export functionality
  exportData(): void {
    const data = this.dataSource.filteredData.map(q => ({
      'Servicio': q.ServiceName,
      'Estación': q.StationName || 'N/A',
      'Ticket Actual': q.CurrentTicketNumber || 'N/A',
      'En Espera': q.QueueLength,
      'Tiempo Promedio': this.formatWaitTime(q.AverageWaitTime),
      'Estado': this.getStatusLabel(q)
    }));

    const csv = this.convertToCSV(data);
    this.downloadCSV(csv, 'estado-colas.csv');
  }

  private convertToCSV(data: any[]): string {
    if (!data.length) return '';

    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');

    const csvRows = data.map(row =>
      headers.map(header => {
        const value = row[header];
        return typeof value === 'string' && value.includes(',') ?
          `"${value}"` : value;
      }).join(',')
    );

    return [csvHeaders, ...csvRows].join('\n');
  }

  private downloadCSV(csv: string, filename: string): void {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
