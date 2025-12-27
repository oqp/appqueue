// station-dialog.component.ts
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

export interface DialogData {
  station?: any;
  serviceTypes: any[];
  isEdit: boolean;
  isViewOnly?: boolean;  // Nueva propiedad
}

@Component({
  selector: 'app-station-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './station-dialog.component.html',
  styleUrls: ['./station-dialog.component.scss']
})
export class StationDialogComponent implements OnInit {
  stationForm: FormGroup;
  loading = false;
  statusOptions = ['Available', 'Maintenance', 'Offline'];

  // Para generar código automático
  private codePrefix = 'V';

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<StationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private snackBar: MatSnackBar
  ) {
    this.stationForm = this.createForm();
  }

  ngOnInit(): void {
    console.log('Data recibida en dialog:', this.data);
    console.log('ServiceTypes:', this.data.serviceTypes);
    if (this.data.isEdit && this.data.station) {
      this.populateForm(this.data.station);
      if (this.isViewOnly) {
        this.stationForm.disable();
      }
    } else {
      // Generar código automático para nueva estación
      this.generateStationCode();
    }
  }

  private createForm(): FormGroup {
    return this.fb.group({
      Code: ['', [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(10),
        Validators.pattern(/^[A-Z0-9]+$/)
      ]],
      Name: ['', [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(100)
      ]],
      Description: ['', [
        Validators.maxLength(200)
      ]],
      ServiceTypeId: [null, Validators.required],
      Location: ['', [
        Validators.maxLength(100)
      ]],
      Status: ['Available', Validators.required],
      IsActive: [true]
    });
  }

  private populateForm(station: any): void {
    this.stationForm.patchValue({
      Code: station.Code,
      Name: station.Name,
      Description: station.Description,
      ServiceTypeId: station.ServiceTypeId,
      Location: station.Location,
      Status: station.Status,
      IsActive: station.IsActive
    });

    // El código no se puede editar en modo edición
    this.stationForm.get('Code')?.disable();
  }

  private generateStationCode(): void {
    // Generar código basado en el tipo de servicio seleccionado
    const serviceTypeControl = this.stationForm.get('ServiceTypeId');

    serviceTypeControl?.valueChanges.subscribe(serviceTypeId => {
      if (serviceTypeId) {
        const serviceType = this.data.serviceTypes.find(st => st.Id === serviceTypeId);
        if (serviceType) {
          const prefix = this.getCodePrefix(serviceType.Name);
          const code = this.generateNextCode(prefix);
          this.stationForm.patchValue({ Code: code });
        }
      }
    });
  }

  private getCodePrefix(serviceTypeName: string): string {
    // Generar prefijo basado en el nombre del servicio
    const prefixMap: { [key: string]: string } = {
      'Análisis': 'VA',
      'Consultas': 'VC',
      'Entrega de Resultados': 'VR',
      'Entrega de Muestras': 'VM',
      'Servicios de Prioridad': 'VP',
      'Rayos X': 'VX',
      'Farmacia': 'VF',
      'Caja': 'VCJ'
    };

    return prefixMap[serviceTypeName] || 'VG'; // VG = Ventanilla General
  }

  private generateNextCode(prefix: string): string {
    // En un caso real, esto debería consultar al backend para obtener el siguiente número
    // Por ahora, generamos uno basado en timestamp
    const number = Math.floor(Math.random() * 99) + 1;
    return `${prefix}${number.toString().padStart(2, '0')}`;
  }

  onSubmit(): void {
    if (this.stationForm.invalid) {
      this.markFormGroupTouched(this.stationForm);
      return;
    }

    this.loading = true;

    // Preparar datos para enviar
    const formValue = this.stationForm.getRawValue(); // getRawValue incluye campos deshabilitados

    // Simular delay de red
    setTimeout(() => {
      this.loading = false;
      this.dialogRef.close(formValue);
    }, 1000);
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  // Utilidades
  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }

  getErrorMessage(fieldName: string): string {
    const control = this.stationForm.get(fieldName);

    if (!control || !control.errors || !control.touched) {
      return '';
    }

    const errors = control.errors;

    if (errors['required']) {
      return `${this.getFieldLabel(fieldName)} es requerido`;
    }

    if (errors['minlength']) {
      return `Mínimo ${errors['minlength'].requiredLength} caracteres`;
    }

    if (errors['maxlength']) {
      return `Máximo ${errors['maxlength'].requiredLength} caracteres`;
    }

    if (errors['pattern']) {
      if (fieldName === 'Code') {
        return 'Solo letras mayúsculas y números';
      }
    }

    return 'Campo inválido';
  }

  private getFieldLabel(fieldName: string): string {
    const labels: { [key: string]: string } = {
      'Code': 'Código',
      'Name': 'Nombre',
      'Description': 'Descripción',
      'ServiceTypeId': 'Tipo de Servicio',
      'Location': 'Ubicación',
      'Status': 'Estado'
    };

    return labels[fieldName] || fieldName;
  }

  // Para el template
  get isEdit(): boolean {
    return this.data.isEdit;
  }

  get isViewOnly(): boolean {
    return this.data.isViewOnly || false;
  }


  get dialogTitle(): string {
    return this.isEdit ? this.isViewOnly? 'Ver Detalles' :'Editar Estación' : 'Nueva Estación';
  }

  get submitButtonText(): string {
    return this.isEdit ? 'Actualizar' : 'Crear';
  }

  // Helper para iconos de servicios
  getServiceIcon(serviceName: string): string {
    const iconMap: { [key: string]: string } = {
      'Análisis': 'biotech',
      'Consultas': 'forum',
      'Entrega de Resultados': 'assignment',
      'Entrega de Muestras': 'science',
      'Servicios de Prioridad': 'priority_high',
      'Rayos X': 'radio_button_checked',
      'Farmacia': 'local_pharmacy'
    };
    return iconMap[serviceName] || 'medical_services';
  }
}
