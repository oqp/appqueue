import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSliderModule } from '@angular/material/slider';
import {ServiceType} from '../../services/service-type.model';


interface DialogData {
  mode: 'create' | 'edit';
  serviceType?: ServiceType;
}

@Component({
  selector: 'app-service-type-dialog',
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
    MatSliderModule
  ],
  templateUrl: './service-type-dialog.component.html',
  styleUrls: ['./service-type-dialog.component.scss']
})
export class ServiceTypeDialogComponent implements OnInit {
  form: FormGroup;
  isEditMode: boolean;
  selectedColor: string = '#007bff';

  priorityOptions = [
    { value: 1, label: 'Máxima', description: 'Atención inmediata' },
    { value: 2, label: 'Alta', description: 'Atención prioritaria' },
    { value: 3, label: 'Media', description: 'Atención normal' },
    { value: 4, label: 'Baja', description: 'Puede esperar' },
    { value: 5, label: 'Mínima', description: 'Sin urgencia' }
  ];

  predefinedColors = [
    '#007bff', // Azul
    '#28a745', // Verde
    '#dc3545', // Rojo
    '#ffc107', // Amarillo
    '#17a2b8', // Cyan
    '#6610f2', // Púrpura
    '#e83e8c', // Rosa
    '#fd7e14'  // Naranja
  ];

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<ServiceTypeDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) {
    this.isEditMode = data.mode === 'edit';

    this.form = this.fb.group({
      Code: [
        { value: data.serviceType?.Code || '', disabled: this.isEditMode },
        [Validators.required, Validators.maxLength(10), Validators.pattern(/^[A-Z0-9]+$/)]
      ],
      Name: [
        data.serviceType?.Name || '',
        [Validators.required, Validators.maxLength(100)]
      ],
      Description: [
        data.serviceType?.Description || '',
        [Validators.maxLength(500)]
      ],
      Priority: [
        data.serviceType?.Priority || 3,
        [Validators.required, Validators.min(1), Validators.max(5)]
      ],
      AverageTimeMinutes: [
        data.serviceType?.AverageTimeMinutes || 10,
        [Validators.required, Validators.min(1), Validators.max(180)]
      ],
      TicketPrefix: [
        data.serviceType?.TicketPrefix || '',
        [Validators.required, Validators.maxLength(5), Validators.pattern(/^[A-Z0-9]+$/)]
      ],
      Color: [
        data.serviceType?.Color || '#007bff',
        [Validators.required, Validators.pattern(/^#[0-9A-Fa-f]{6}$/)]
      ]
    });

    if (data.serviceType?.Color) {
      this.selectedColor = data.serviceType.Color;
    }
  }

  ngOnInit(): void {
    // Auto-generar prefijo basado en el código si es modo creación
    if (!this.isEditMode) {
      this.form.get('Code')?.valueChanges.subscribe(code => {
        if (code && !this.form.get('TicketPrefix')?.value) {
          const prefix = code.substring(0, 3).toUpperCase();
          this.form.patchValue({ TicketPrefix: prefix }, { emitEvent: false });
        }
      });
    }
  }

  onColorSelect(color: string): void {
    this.selectedColor = color;
    this.form.patchValue({ Color: color });
  }

  onColorInputChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedColor = input.value;
    this.form.patchValue({ Color: input.value });
  }

  formatTimeLabel(value: number): string {
    if (value === 1) return '1 min';
    if (value < 60) return `${value} min`;
    const hours = Math.floor(value / 60);
    const minutes = value % 60;
    if (minutes === 0) return `${hours}h`;
    return `${hours}h ${minutes}min`;
  }

  onSubmit(): void {
    if (this.form.valid) {
      const formValue = this.form.getRawValue();

      // Asegurar que el código y prefijo estén en mayúsculas
      formValue.Code = formValue.Code.toUpperCase();
      formValue.TicketPrefix = formValue.TicketPrefix.toUpperCase();

      this.dialogRef.close(formValue);
    } else {
      // Marcar todos los campos como tocados para mostrar errores
      Object.keys(this.form.controls).forEach(key => {
        this.form.get(key)?.markAsTouched();
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  getErrorMessage(fieldName: string): string {
    const control = this.form.get(fieldName);

    if (control?.hasError('required')) {
      return `${this.getFieldLabel(fieldName)} es requerido`;
    }

    if (control?.hasError('maxlength')) {
      const maxLength = control.errors?.['maxlength'].requiredLength;
      return `Máximo ${maxLength} caracteres`;
    }

    if (control?.hasError('pattern')) {
      if (fieldName === 'Code' || fieldName === 'TicketPrefix') {
        return 'Solo letras mayúsculas y números';
      }
      if (fieldName === 'Color') {
        return 'Formato hexadecimal inválido';
      }
    }

    if (control?.hasError('min') || control?.hasError('max')) {
      if (fieldName === 'Priority') {
        return 'La prioridad debe estar entre 1 y 5';
      }
      if (fieldName === 'AverageTimeMinutes') {
        return 'El tiempo debe estar entre 1 y 180 minutos';
      }
    }

    return '';
  }

  private getFieldLabel(fieldName: string): string {
    const labels: { [key: string]: string } = {
      'Code': 'Código',
      'Name': 'Nombre',
      'Description': 'Descripción',
      'Priority': 'Prioridad',
      'AverageTimeMinutes': 'Tiempo promedio',
      'TicketPrefix': 'Prefijo de ticket',
      'Color': 'Color'
    };
    return labels[fieldName] || fieldName;
  }
}
