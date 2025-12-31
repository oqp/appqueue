import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

interface Patient {
  id: string;
  document_number: string;
  full_name: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  gender: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
}

interface DialogData {
  patient: Patient | null;
  isEdit: boolean;
}

@Component({
  selector: 'app-patient-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSlideToggleModule
  ],
  templateUrl: './patient-dialog.component.html',
  styleUrls: ['./patient-dialog.component.scss']
})
export class PatientDialogComponent implements OnInit {
  form!: FormGroup;
  isEdit: boolean;
  maxDate = new Date();

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<PatientDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) {
    this.isEdit = data.isEdit;
  }

  ngOnInit(): void {
    this.initForm();

    if (this.isEdit && this.data.patient) {
      this.populateForm(this.data.patient);
    }
  }

  private initForm(): void {
    this.form = this.fb.group({
      document_number: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(20)]],
      first_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
      last_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
      birth_date: [null],
      gender: ['', Validators.required],
      phone: ['', [Validators.maxLength(20)]],
      email: ['', [Validators.email, Validators.maxLength(100)]],
      is_active: [true]
    });
  }

  private populateForm(patient: Patient): void {
    this.form.patchValue({
      document_number: patient.document_number,
      first_name: patient.first_name || '',
      last_name: patient.last_name || '',
      birth_date: patient.birth_date ? new Date(patient.birth_date) : null,
      gender: patient.gender,
      phone: patient.phone || '',
      email: patient.email || '',
      is_active: patient.is_active
    });
  }

  onSubmit(): void {
    if (this.form.valid) {
      const formValue = { ...this.form.value };

      // Format date for API
      if (formValue.birth_date instanceof Date) {
        formValue.birth_date = formValue.birth_date.toISOString().split('T')[0];
      }

      // Clean empty strings
      if (!formValue.phone) formValue.phone = null;
      if (!formValue.email) formValue.email = null;

      this.dialogRef.close(formValue);
    }
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }

  getErrorMessage(field: string): string {
    const control = this.form.get(field);
    if (!control) return '';

    if (control.hasError('required')) {
      return 'Este campo es requerido';
    }
    if (control.hasError('minlength')) {
      const minLength = control.getError('minlength').requiredLength;
      return `Mínimo ${minLength} caracteres`;
    }
    if (control.hasError('maxlength')) {
      const maxLength = control.getError('maxlength').requiredLength;
      return `Máximo ${maxLength} caracteres`;
    }
    if (control.hasError('email')) {
      return 'Email inválido';
    }
    return '';
  }
}
