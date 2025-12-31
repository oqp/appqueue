// user-dialog.component.ts
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';

interface Role {
  Id: number;
  Name: string;
  Description?: string;
  IsActive: boolean;
}

interface Station {
  Id: number;
  Name: string;
  Code: string;
  IsActive: boolean;
}

interface UserResponse {
  Id: string;
  Username: string;
  Email: string;
  FullName: string;
  IsActive: boolean;
  RoleId: number;
  role_name?: string;
  StationId?: number;
  station_name?: string;
  station_code?: string;
  CreatedAt: Date;
  UpdatedAt?: Date;
  LastLogin?: Date;
}

interface DialogData {
  user: UserResponse | null;
  roles: Role[];
  stations: Station[];
  isEdit: boolean;
  isViewOnly?: boolean;
  canAssignRole?: boolean;
}

@Component({
  selector: 'app-user-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatDividerModule,
    MatTooltipModule
  ],
  template: `
    <div class="user-dialog">
      <h2 mat-dialog-title>
        <mat-icon>{{ data.isViewOnly ? 'person' : (data.isEdit ? 'edit' : 'person_add') }}</mat-icon>
        {{ getTitle() }}
      </h2>

      <mat-dialog-content>
        <form [formGroup]="userForm" class="user-form">
          <!-- Informacion basica -->
          <div class="form-section">
            <h4>Informacion Basica</h4>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Nombre de Usuario</mat-label>
                <input matInput formControlName="Username" placeholder="usuario123">
                <mat-icon matPrefix>account_circle</mat-icon>
                <mat-error *ngIf="userForm.get('Username')?.hasError('required')">
                  El usuario es requerido
                </mat-error>
                <mat-error *ngIf="userForm.get('Username')?.hasError('minlength')">
                  Minimo 3 caracteres
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Nombre Completo</mat-label>
                <input matInput formControlName="FullName" placeholder="Juan Perez">
                <mat-icon matPrefix>badge</mat-icon>
                <mat-error *ngIf="userForm.get('FullName')?.hasError('required')">
                  El nombre es requerido
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Email</mat-label>
                <input matInput formControlName="Email" placeholder="usuario@email.com" type="email">
                <mat-icon matPrefix>email</mat-icon>
                <mat-error *ngIf="userForm.get('Email')?.hasError('required')">
                  El email es requerido
                </mat-error>
                <mat-error *ngIf="userForm.get('Email')?.hasError('email')">
                  Email invalido
                </mat-error>
              </mat-form-field>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- Contrasena (solo para crear) -->
          <div class="form-section" *ngIf="!data.isEdit && !data.isViewOnly">
            <h4>Contrasena</h4>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Contrasena</mat-label>
                <input matInput formControlName="Password"
                       [type]="hidePassword ? 'password' : 'text'"
                       placeholder="Minimo 8 caracteres">
                <mat-icon matPrefix>lock</mat-icon>
                <button mat-icon-button matSuffix type="button"
                        (click)="hidePassword = !hidePassword">
                  <mat-icon>{{ hidePassword ? 'visibility_off' : 'visibility' }}</mat-icon>
                </button>
                <mat-error *ngIf="userForm.get('Password')?.hasError('required')">
                  La contrasena es requerida
                </mat-error>
                <mat-error *ngIf="userForm.get('Password')?.hasError('minlength')">
                  Minimo 8 caracteres
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Confirmar Contrasena</mat-label>
                <input matInput formControlName="ConfirmPassword"
                       [type]="hidePassword ? 'password' : 'text'"
                       placeholder="Repetir contrasena">
                <mat-icon matPrefix>lock_outline</mat-icon>
                <mat-error *ngIf="userForm.get('ConfirmPassword')?.hasError('required')">
                  Confirme la contrasena
                </mat-error>
                <mat-error *ngIf="userForm.get('ConfirmPassword')?.hasError('mismatch')">
                  Las contrasenas no coinciden
                </mat-error>
              </mat-form-field>
            </div>
          </div>

          <mat-divider *ngIf="!data.isEdit && !data.isViewOnly"></mat-divider>

          <!-- Rol y Estacion -->
          <div class="form-section">
            <h4>Rol y Asignacion</h4>

            <div class="form-row two-columns">
              <mat-form-field appearance="outline">
                <mat-label>Rol</mat-label>
                <mat-select formControlName="RoleId">
                  <mat-option *ngFor="let role of data.roles" [value]="role.Id">
                    {{ role.Name }}
                  </mat-option>
                </mat-select>
                <mat-icon matPrefix>security</mat-icon>
                <mat-error *ngIf="userForm.get('RoleId')?.hasError('required')">
                  El rol es requerido
                </mat-error>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Estacion</mat-label>
                <mat-select formControlName="StationId">
                  <mat-option [value]="null">Sin asignar</mat-option>
                  <mat-option *ngFor="let station of data.stations" [value]="station.Id">
                    {{ station.Code }} - {{ station.Name }}
                  </mat-option>
                </mat-select>
                <mat-icon matPrefix>desktop_windows</mat-icon>
              </mat-form-field>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- Estado -->
          <div class="form-section" *ngIf="data.isEdit">
            <h4>Estado</h4>

            <mat-checkbox formControlName="IsActive" color="primary">
              Usuario Activo
            </mat-checkbox>
          </div>

          <!-- Info adicional (solo vista) -->
          <div class="form-section info-section" *ngIf="data.isViewOnly && data.user">
            <h4>Informacion Adicional</h4>

            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Creado:</span>
                <span class="info-value">{{ formatDate(data.user.CreatedAt) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Actualizado:</span>
                <span class="info-value">{{ formatDate(data.user.UpdatedAt) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Ultimo acceso:</span>
                <span class="info-value">{{ formatDate(data.user.LastLogin) || 'Nunca' }}</span>
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
                [disabled]="userForm.invalid"
                (click)="onSave()">
          <mat-icon>{{ data.isEdit ? 'save' : 'person_add' }}</mat-icon>
          {{ data.isEdit ? 'Guardar Cambios' : 'Crear Usuario' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .user-dialog {
      min-width: 500px;
      max-width: 600px;
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
      max-height: 70vh;
    }

    .user-form {
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
    }

    .form-row {
      margin-bottom: 8px;

      &.two-columns {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
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
      }
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
      .user-dialog {
        min-width: auto;
        width: 100%;
      }

      .form-row.two-columns {
        grid-template-columns: 1fr;
      }

      .info-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class UserDialogComponent implements OnInit {
  userForm: FormGroup;
  hidePassword = true;

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<UserDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) {
    this.userForm = this.createForm();
  }

  ngOnInit(): void {
    if (this.data.user) {
      this.populateForm();
    }

    if (this.data.isViewOnly) {
      this.userForm.disable();
    }

    // Deshabilitar rol si no tiene permisos
    if (this.data.isEdit && !this.data.canAssignRole) {
      this.userForm.get('RoleId')?.disable();
    }
  }

  private createForm(): FormGroup {
    const form = this.fb.group({
      Username: ['', [Validators.required, Validators.minLength(3)]],
      FullName: ['', [Validators.required, Validators.minLength(2)]],
      Email: ['', [Validators.required, Validators.email]],
      Password: [''],
      ConfirmPassword: [''],
      RoleId: [null, Validators.required],
      StationId: [null],
      IsActive: [true]
    });

    // Validaciones de contrasena solo para crear
    if (!this.data.isEdit) {
      form.get('Password')?.setValidators([Validators.required, Validators.minLength(8)]);
      form.get('ConfirmPassword')?.setValidators([Validators.required]);

      // Validar que las contrasenas coincidan
      form.get('ConfirmPassword')?.valueChanges.subscribe(value => {
        const password = form.get('Password')?.value;
        if (value && password !== value) {
          form.get('ConfirmPassword')?.setErrors({ mismatch: true });
        }
      });
    }

    return form;
  }

  private populateForm(): void {
    if (!this.data.user) return;

    this.userForm.patchValue({
      Username: this.data.user.Username,
      FullName: this.data.user.FullName,
      Email: this.data.user.Email,
      RoleId: this.data.user.RoleId,
      StationId: this.data.user.StationId,
      IsActive: this.data.user.IsActive
    });

    // Deshabilitar username en edicion
    if (this.data.isEdit) {
      this.userForm.get('Username')?.disable();
    }
  }

  getTitle(): string {
    if (this.data.isViewOnly) {
      return 'Detalles del Usuario';
    }
    return this.data.isEdit ? 'Editar Usuario' : 'Nuevo Usuario';
  }

  formatDate(date: Date | string | undefined): string {
    if (!date) return '-';
    const d = new Date(date);
    return d.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.userForm.invalid) return;

    const formValue = this.userForm.getRawValue();

    // Preparar datos para enviar
    const userData: any = {
      FullName: formValue.FullName,
      Email: formValue.Email,
      RoleId: formValue.RoleId,
      StationId: formValue.StationId
    };

    if (!this.data.isEdit) {
      // Datos adicionales para crear
      userData.Username = formValue.Username;
      userData.Password = formValue.Password;
      userData.IsActive = true;
    } else {
      // Datos para editar
      userData.IsActive = formValue.IsActive;
    }

    this.dialogRef.close(userData);
  }
}
