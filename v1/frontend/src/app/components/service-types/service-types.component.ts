import { Component, OnInit, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ServiceTypesService } from '../../services/service-types.service';
import {ServiceType} from '../../services/service-type.model';
import {ServiceTypeDialogComponent} from '../service-type-dialog/service-type-dialog.component';
import {MatCheckboxModule} from '@angular/material/checkbox';


@Component({
  selector: 'app-service-types',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCardModule,
    MatCheckboxModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule
  ],
  templateUrl: './service-types.component.html',
  styleUrls: ['./service-types.component.scss']
})
export class ServiceTypesComponent implements OnInit {
  displayedColumns: string[] = [
    'Code',
    'Name',
    'Priority',
    'TicketPrefix',
    'AverageTimeMinutes',
    'Color',
    'IsActive',
    'actions'
  ];

  dataSource = new MatTableDataSource<ServiceType>([]);
  loading = signal(false);
  totalServices = signal(0);
  activeServices = signal(0);
  inactiveServices = signal(0);

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  filterForm: FormGroup;
  priorityOptions = [
    { value: 1, label: 'Máxima' },
    { value: 2, label: 'Alta' },
    { value: 3, label: 'Media' },
    { value: 4, label: 'Baja' },
    { value: 5, label: 'Mínima' }
  ];

  constructor(
    private fb: FormBuilder,
    private serviceTypesService: ServiceTypesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.filterForm = this.fb.group({
      searchText: [''],
      priority: [''],
      activeOnly: [true]
    });
  }

  ngOnInit(): void {
    this.loadServiceTypes();
    this.setupFilterListener();
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  setupFilterListener(): void {
    this.filterForm.valueChanges.subscribe(() => {
      this.applyFilter();
    });
  }

  loadServiceTypes(): void {
    this.loading.set(true);
    console.log('Loading service types...');

    const filters = this.filterForm.value;

    this.serviceTypesService.getServiceTypes(
      0,
      100,
      filters.activeOnly,
      filters.priority || null
    ).subscribe({
      next: (response) => {
        console.log('Service types response:', response);

        // Manejar diferentes formatos de respuesta
        if (response && response.services) {
          this.dataSource.data = response.services;
          this.totalServices.set(response.total || response.services.length);
          this.activeServices.set(response.active_count || 0);
          this.inactiveServices.set(response.inactive_count || 0);
        } else if (Array.isArray(response)) {
          // Si la respuesta es directamente un array
          this.dataSource.data = response;
          this.totalServices.set(response.length);
          const active = response.filter((s: any) => s.IsActive).length;
          this.activeServices.set(active);
          this.inactiveServices.set(response.length - active);
        } else {
          console.warn('Unexpected response format:', response);
          this.dataSource.data = [];
        }

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading service types:', error);

        // Mostrar mensaje de error más específico
        let errorMessage = 'Error al cargar los tipos de atenciones';
        if (error.status === 404) {
          errorMessage = 'El endpoint no fue encontrado. Verifique la configuración del API.';
        } else if (error.status === 401) {
          errorMessage = 'No está autorizado. Por favor, inicie sesión.';
        } else if (error.status === 0) {
          errorMessage = 'No se pudo conectar con el servidor. Verifique que el backend esté ejecutándose.';
        }

        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });

        this.loading.set(false);
      }
    });
  }

  applyFilter(): void {
    const filterValue = this.filterForm.get('searchText')?.value || '';
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(ServiceTypeDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      panelClass: 'full-width-dialog',
      data: { mode: 'create' }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.createServiceType(result);
      }
    });
  }

  openEditDialog(serviceType: ServiceType): void {
    const dialogRef = this.dialog.open(ServiceTypeDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      panelClass: 'full-width-dialog',
      data: {
        mode: 'edit',
        serviceType: { ...serviceType }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updateServiceType(serviceType.Id, result);
      }
    });
  }

  createServiceType(serviceData: Partial<ServiceType>): void {
    this.loading.set(true);

    this.serviceTypesService.createServiceType(serviceData).subscribe({
      next: (response) => {
        this.snackBar.open('Tipo de atención creado exitosamente', 'Cerrar', {
          duration: 3000,
          panelClass: ['success-snackbar']
        });
        this.loadServiceTypes();
      },
      error: (error) => {
        console.error('Error creating service type:', error);
        this.snackBar.open(
          error.error?.detail || 'Error al crear el tipo de atención',
          'Cerrar',
          {
            duration: 3000,
            panelClass: ['error-snackbar']
          }
        );
        this.loading.set(false);
      }
    });
  }

  updateServiceType(id: number, serviceData: Partial<ServiceType>): void {
    this.loading.set(true);

    this.serviceTypesService.updateServiceType(id, serviceData).subscribe({
      next: (response) => {
        this.snackBar.open('Tipo de atención actualizado exitosamente', 'Cerrar', {
          duration: 3000,
          panelClass: ['success-snackbar']
        });
        this.loadServiceTypes();
      },
      error: (error) => {
        console.error('Error updating service type:', error);
        this.snackBar.open(
          error.error?.detail || 'Error al actualizar el tipo de atención',
          'Cerrar',
          {
            duration: 3000,
            panelClass: ['error-snackbar']
          }
        );
        this.loading.set(false);
      }
    });
  }

  toggleServiceStatus(serviceType: ServiceType): void {
    const newStatus = !serviceType.IsActive;
    const updateData = { IsActive: newStatus };

    this.serviceTypesService.updateServiceType(serviceType.Id, updateData).subscribe({
      next: () => {
        serviceType.IsActive = newStatus;
        this.snackBar.open(
          `Tipo de atención ${newStatus ? 'activado' : 'desactivado'}`,
          'Cerrar',
          {
            duration: 2000,
            panelClass: ['success-snackbar']
          }
        );
        this.loadServiceTypes();
      },
      error: (error) => {
        console.error('Error toggling service status:', error);
        this.snackBar.open('Error al cambiar el estado', 'Cerrar', {
          duration: 3000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }

  deleteServiceType(serviceType: ServiceType): void {
    if (confirm(`¿Está seguro de eliminar el tipo de atención "${serviceType.Name}"?`)) {
      this.loading.set(true);

      // Soft delete (desactivar)
      this.toggleServiceStatus(serviceType);
    }
  }

  getPriorityLabel(priority: number): string {
    const option = this.priorityOptions.find(opt => opt.value === priority);
    return option ? option.label : 'Desconocida';
  }

  getPriorityClass(priority: number): string {
    switch (priority) {
      case 1: return 'max';
      case 2: return 'high';
      case 3: return 'medium';
      case 4: return 'low';
      case 5: return 'min';
      default: return '';
    }
  }

  refreshData(): void {
    this.loadServiceTypes();
  }
}
