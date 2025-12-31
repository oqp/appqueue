import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface PatientNotFoundDialogData {
  documentNumber: string;
}

export interface PatientNotFoundDialogResult {
  action: 'generate_without_dni' | 'cancel';
}

@Component({
  selector: 'app-patient-not-found-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="dialog-container">
      <div class="dialog-icon">
        <mat-icon>person_off</mat-icon>
      </div>

      <h2 mat-dialog-title>Paciente No Encontrado</h2>

      <mat-dialog-content>
        <p class="message">
          No se encontró ningún paciente con el documento
          <strong>{{ data.documentNumber }}</strong>
          en la base de datos local ni en el servicio de DNI.
        </p>

        <p class="question">
          ¿Desea generar un ticket de todas formas?
        </p>

        <p class="note">
          <mat-icon>info</mat-icon>
          El ticket se generará sin información del paciente.
        </p>
      </mat-dialog-content>

      <mat-dialog-actions align="center">
        <button
          mat-raised-button
          (click)="onCancel()"
          class="cancel-button">
          <mat-icon>close</mat-icon>
          CANCELAR
        </button>

        <button
          mat-raised-button
          color="primary"
          (click)="onGenerateWithoutDni()"
          class="generate-button">
          <mat-icon>confirmation_number</mat-icon>
          GENERAR TICKET SIN DNI
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .dialog-container {
      text-align: center;
      padding: 20px;
    }

    .dialog-icon {
      margin-bottom: 16px;

      mat-icon {
        font-size: 64px;
        width: 64px;
        height: 64px;
        color: #f44336;
      }
    }

    h2[mat-dialog-title] {
      margin: 0 0 16px;
      font-size: 24px;
      font-weight: 500;
      color: #333;
    }

    mat-dialog-content {
      padding: 0 24px;
    }

    .message {
      font-size: 16px;
      color: #666;
      margin-bottom: 16px;

      strong {
        color: #1565c0;
        font-family: monospace;
        font-size: 18px;
      }
    }

    .question {
      font-size: 18px;
      font-weight: 500;
      color: #333;
      margin: 24px 0;
    }

    .note {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-size: 14px;
      color: #ff9800;
      background: #fff3e0;
      padding: 12px 16px;
      border-radius: 8px;
      margin-top: 16px;

      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    mat-dialog-actions {
      padding: 24px;
      gap: 16px;

      button {
        min-width: 200px;
        height: 48px;
        font-size: 14px;
        font-weight: 500;

        mat-icon {
          margin-right: 8px;
        }
      }

      .cancel-button {
        background: #f5f5f5;
        color: #666;
      }

      .generate-button {
        background: #4caf50;
        color: white;
      }
    }
  `]
})
export class PatientNotFoundDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<PatientNotFoundDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PatientNotFoundDialogData
  ) {}

  onCancel(): void {
    this.dialogRef.close({ action: 'cancel' } as PatientNotFoundDialogResult);
  }

  onGenerateWithoutDni(): void {
    this.dialogRef.close({ action: 'generate_without_dni' } as PatientNotFoundDialogResult);
  }
}
