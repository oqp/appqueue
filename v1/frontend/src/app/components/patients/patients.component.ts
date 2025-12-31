import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subject, takeUntil } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environments';
import { AuthService } from '../../services/auth.service';
import { PatientDialogComponent } from '../patient-dialog/patient-dialog.component';

interface Patient {
  id: string;
  document_number: string;
  full_name: string;
  birth_date: string;
  gender: string;
  phone: string | null;
  email: string | null;
  age: number;
  is_active: boolean;
  CreatedAt: string;
}

@Component({
  selector: 'app-patients',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './patients.component.html',
  styleUrls: ['./patients.component.scss']
})
export class PatientsComponent implements OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  dataSource = new MatTableDataSource<Patient>([]);
  displayedColumns: string[] = ['document_number', 'full_name', 'status', 'actions'];

  loading = false;
  searchTerm = '';

  // Stats
  totalPatients = 0;
  activePatients = 0;

  private destroy$ = new Subject<void>();
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadPatients();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  loadPatients(): void {
    this.loading = true;

    const params = this.searchTerm ? `?search=${encodeURIComponent(this.searchTerm)}` : '';

    this.http.get<Patient[]>(`${this.apiUrl}/patients${params}`, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (patients) => {
        this.dataSource.data = patients;
        this.totalPatients = patients.length;
        this.activePatients = patients.filter(p => p.is_active).length;

        setTimeout(() => {
          if (this.paginator) {
            this.dataSource.paginator = this.paginator;
          }
          if (this.sort) {
            this.dataSource.sort = this.sort;
          }
        });

        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.showError('Error al cargar los pacientes');
        console.error('Error loading patients:', error);
      }
    });
  }

  applyFilter(): void {
    this.loadPatients();
  }

  clearSearch(): void {
    this.searchTerm = '';
    this.loadPatients();
  }

  createPatient(): void {
    const dialogRef = this.dialog.open(PatientDialogComponent, {
      width: '500px',
      maxWidth: '95vw',
      data: { patient: null, isEdit: false },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.savePatient(result);
      }
    });
  }

  editPatient(patient: Patient): void {
    const dialogRef = this.dialog.open(PatientDialogComponent, {
      width: '500px',
      maxWidth: '95vw',
      data: { patient: patient, isEdit: true },
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updatePatient(patient.id, result);
      }
    });
  }

  private savePatient(patientData: any): void {
    this.loading = true;

    this.http.post<Patient>(`${this.apiUrl}/patients`, patientData, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.showSuccess('Paciente creado exitosamente');
        this.loadPatients();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.error?.detail || 'Error al crear el paciente');
      }
    });
  }

  private updatePatient(patientId: string, patientData: any): void {
    this.loading = true;

    this.http.put<Patient>(`${this.apiUrl}/patients/${patientId}`, patientData, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.showSuccess('Paciente actualizado exitosamente');
        this.loadPatients();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.error?.detail || 'Error al actualizar el paciente');
      }
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
