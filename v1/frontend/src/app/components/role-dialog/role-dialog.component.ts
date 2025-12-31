// role-dialog.component.ts
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';

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

interface DialogData {
  role: Role | null;
  isEdit: boolean;
  isViewOnly?: boolean;
}

@Component({
  selector: 'app-role-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatDividerModule,
    MatChipsModule,
    MatTooltipModule
  ],
  template: `
    <div class="role-dialog">
      <h2 mat-dialog-title>
        <mat-icon>{{ data.isViewOnly ? 'security' : (data.isEdit ? 'edit' : 'add_circle') }}</mat-icon>
        {{ getTitle() }}
      </h2>

      <mat-dialog-content>
        <form [formGroup]="roleForm" class="role-form">
          <!-- Informacion basica -->
          <div class="form-section">
            <h4>Informacion del Rol</h4>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Nombre del Rol</mat-label>
                <input matInput formControlName="Name" placeholder="Ej: Supervisor">
                <mat-icon matPrefix>badge</mat-icon>
                <mat-error *ngIf="roleForm.get('Name')?.hasError('required')">
                  El nombre es requerido
                </mat-error>
                <mat-error *ngIf="roleForm.get('Name')?.hasError('minlength')">
                  Minimo 2 caracteres
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Descripcion</mat-label>
                <textarea matInput formControlName="Description"
                          placeholder="Descripcion del rol y sus responsabilidades"
                          rows="3"></textarea>
                <mat-icon matPrefix>description</mat-icon>
                <mat-hint align="end">{{ roleForm.get('Description')?.value?.length || 0 }}/200</mat-hint>
              </mat-form-field>
            </div>
          </div>

          <mat-divider *ngIf="data.isEdit"></mat-divider>

          <!-- Estado (solo para editar) -->
          <div class="form-section" *ngIf="data.isEdit && !data.isViewOnly">
            <h4>Estado</h4>
            <mat-checkbox formControlName="IsActive" color="primary">
              Rol Activo
            </mat-checkbox>
            <p class="hint-text" *ngIf="data.role && data.role.UserCount && data.role.UserCount > 0">
              <mat-icon>info</mat-icon>
              Este rol tiene {{ data.role.UserCount }} usuario(s) asignado(s)
            </p>
          </div>

          <!-- Info adicional (solo vista) -->
          <div class="form-section info-section" *ngIf="data.isViewOnly && data.role">
            <mat-divider></mat-divider>
            <h4>Informacion Adicional</h4>

            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Estado:</span>
                <span class="info-value" [class.active]="data.role.IsActive" [class.inactive]="!data.role.IsActive">
                  {{ data.role.IsActive ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">Usuarios:</span>
                <span class="info-value">{{ data.role.UserCount || 0 }}</span>
              </div>
              <div class="info-item" *ngIf="data.role.CreatedAt">
                <span class="info-label">Creado:</span>
                <span class="info-value">{{ formatDate(data.role.CreatedAt) }}</span>
              </div>
            </div>

            <div class="permissions-section" *ngIf="data.role.Permissions && data.role.Permissions.length > 0">
              <h5>Permisos:</h5>
              <div class="permissions-list">
                <mat-chip *ngFor="let permission of data.role.Permissions" class="permission-chip">
                  {{ permission }}
                </mat-chip>
              </div>
            </div>
          </div>
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()">
          {{ data.isViewOnly ? 'Cerrar' : 'Cancelar' }}
        </button>
        <button mat-raised-button color="primary"
                *ngIf="!data.isViewOnly"
                [disabled]="roleForm.invalid"
                (click)="onSave()">
          <mat-icon>{{ data.isEdit ? 'save' : 'add' }}</mat-icon>
          {{ data.isEdit ? 'Guardar Cambios' : 'Crear Rol' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .role-dialog {
      min-width: 400px;
      max-width: 500px;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      padding: 16px 24px;
      background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
      color: white;
      font-size: 18px;

      mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
      }
    }

    mat-dialog-content {
      padding: 0 !important;
      max-height: 60vh;
    }

    .role-form {
      padding: 0;
    }

    .form-section {
      padding: 16px 24px;

      h4 {
        margin: 0 0 12px 0;
        font-size: 13px;
        font-weight: 600;
        color: #1565C0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      h5 {
        margin: 12px 0 8px 0;
        font-size: 12px;
        font-weight: 600;
        color: #666;
      }
    }

    .form-row {
      margin-bottom: 8px;
    }

    .full-width {
      width: 100%;
    }

    mat-form-field {
      width: 100%;

      mat-icon[matPrefix] {
        margin-right: 8px;
        color: #666;
      }
    }

    mat-divider {
      margin: 0;
    }

    mat-checkbox {
      margin-top: 8px;
    }

    .hint-text {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 11px;
      color: #666;

      mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
        color: #1976d2;
      }
    }

    .info-section {
      background: rgba(68, 119, 255, 0.05);
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 2px;

      .info-label {
        font-size: 10px;
        color: #666;
        text-transform: uppercase;
      }

      .info-value {
        font-size: 12px;
        font-weight: 500;
        color: #333;

        &.active {
          color: #2e7d32;
        }

        &.inactive {
          color: #757575;
        }
      }
    }

    .permissions-section {
      margin-top: 16px;
    }

    .permissions-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .permission-chip {
      font-size: 10px !important;
      height: 22px !important;
      padding: 0 8px !important;
      background-color: rgba(68, 119, 255, 0.1) !important;
      color: #1565c0 !important;
    }

    mat-dialog-actions {
      padding: 12px 24px;
      border-top: 1px solid rgba(0, 0, 0, 0.12);
      margin: 0;

      button {
        margin-left: 8px;

        mat-icon {
          margin-right: 4px;
          font-size: 18px;
          width: 18px;
          height: 18px;
        }
      }
    }

    ::ng-deep {
      .mat-mdc-form-field-infix {
        min-height: 44px;
      }

      .mdc-text-field--outlined {
        --mdc-outlined-text-field-container-shape: 6px;
      }
    }

    @media (max-width: 600px) {
      .role-dialog {
        min-width: auto;
        width: 100%;
      }

      .info-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class RoleDialogComponent implements OnInit {
  roleForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<RoleDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) {
    this.roleForm = this.createForm();
  }

  ngOnInit(): void {
    if (this.data.role) {
      this.populateForm();
    }

    if (this.data.isViewOnly) {
      this.roleForm.disable();
    }
  }

  private createForm(): FormGroup {
    return this.fb.group({
      Name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(50)]],
      Description: ['', [Validators.maxLength(200)]],
      IsActive: [true]
    });
  }

  private populateForm(): void {
    if (!this.data.role) return;

    this.roleForm.patchValue({
      Name: this.data.role.Name,
      Description: this.data.role.Description,
      IsActive: this.data.role.IsActive
    });

    // Deshabilitar nombre en edicion si tiene usuarios
    if (this.data.isEdit && this.data.role.UserCount && this.data.role.UserCount > 0) {
      this.roleForm.get('Name')?.disable();
    }
  }

  getTitle(): string {
    if (this.data.isViewOnly) {
      return 'Detalles del Rol';
    }
    return this.data.isEdit ? 'Editar Rol' : 'Nuevo Rol';
  }

  formatDate(date: string | undefined): string {
    if (!date) return '-';
    const d = new Date(date);
    return d.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.roleForm.invalid) return;

    const formValue = this.roleForm.getRawValue();

    const roleData: any = {
      Name: formValue.Name,
      Description: formValue.Description || null
    };

    if (this.data.isEdit) {
      roleData.IsActive = formValue.IsActive;
    }

    this.dialogRef.close(roleData);
  }
}
