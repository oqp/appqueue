import {Component, OnInit, OnDestroy, HostListener} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDividerModule } from '@angular/material/divider';

// Services and Interfaces
import {
  TicketService,
  Patient,
  ServiceType,
  Ticket,
  PatientCreate,
  TicketQuickCreate
} from '../../services/ticket.service';
import {MatTooltip} from '@angular/material/tooltip';
import {VirtualKeyboardComponent} from '../virtual-keyboard/virtual-keyboard.component';

@Component({
  selector: 'app-ticket-generation',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatDividerModule,
    MatTooltip
  ],
  templateUrl: './ticket-generation.component.html',
  styleUrls: ['./ticket-generation.component.scss'],
  host: {
    '[class.kiosk-mode]': 'isKioskMode'
  }
})
export class TicketGenerationComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  isKioskMode = true;

  // Estados
  isSearching = false;
  isCreatingTicket = false;
  showPatientForm = false;
  currentPatient: Patient | null = null;
  serviceTypes: ServiceType[] = [];
  generatedTicket: Ticket | null = null;
  selectedServiceType: ServiceType | null = null;

  // Formularios
  searchForm: FormGroup;
  patientForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private ticketService: TicketService,
    private snackBar: MatSnackBar
  ) {
    // Formulario de búsqueda
    this.searchForm = this.fb.group({
      documentNumber: ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(20),
        Validators.pattern('^[0-9]+$')
      ]]
    });

    // Formulario de registro de paciente
    this.patientForm = this.fb.group({
      documentNumber: [{value: '', disabled: true}],
      fullName: ['', [Validators.required, Validators.minLength(3)]],
      birthDate: ['', Validators.required],
      gender: ['', Validators.required],
      phone: [''],
      email: ['', [Validators.email]]
    });
  }

  ngOnInit(): void {
    this.loadServiceTypes();
    this.enterKioskMode();
    this.enterFullscreen();
  }

  ngOnDestroy(): void {
    this.exitKioskMode();
    this.exitFullscreen();
    this.destroy$.next();
    this.destroy$.complete();
  }

  get isFullscreen(): boolean {
    return !!(document.fullscreenElement ||
      (document as any).webkitFullscreenElement ||
      (document as any).msFullscreenElement ||
      (document as any).mozFullScreenElement);
  }

  /**
   * Entra en modo pantalla completa del navegador
   */
  protected enterFullscreen(): void {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(err => {
        console.log('Error al entrar en fullscreen:', err);
      });
    } else if ((elem as any).webkitRequestFullscreen) {
      (elem as any).webkitRequestFullscreen();
    } else if ((elem as any).msRequestFullscreen) {
      (elem as any).msRequestFullscreen();
    } else if ((elem as any).mozRequestFullScreen) {
      (elem as any).mozRequestFullScreen();
    }
  }

  /**
   * Sale del modo pantalla completa
   */
  private exitFullscreen(): void {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(err => {
        console.log('Error al salir de fullscreen:', err);
      });
    } else if ((document as any).webkitExitFullscreen) {
      (document as any).webkitExitFullscreen();
    } else if ((document as any).msExitFullscreen) {
      (document as any).msExitFullscreen();
    } else if ((document as any).mozCancelFullScreen) {
      (document as any).mozCancelFullScreen();
    }
  }

  /**
   * Activa el modo kiosko
   */
  private enterKioskMode(): void {
    // Ocultar el sidebar
    const sidebar = document.querySelector('app-sidebar');
    if (sidebar) {
      (sidebar as HTMLElement).style.display = 'none';
    }

    // Ocultar el header si es necesario
    const header = document.querySelector('app-header');
    if (header) {
      (header as HTMLElement).style.display = 'none';
    }

    // Agregar clase al body para modo kiosko
    document.body.classList.add('kiosk-mode-active');
  }

  /**
   * Desactiva el modo kiosko al salir del componente
   */
  private exitKioskMode(): void {
    // Restaurar el sidebar
    const sidebar = document.querySelector('app-sidebar');
    if (sidebar) {
      (sidebar as HTMLElement).style.display = '';
    }

    // Restaurar el header
    const header = document.querySelector('app-header');
    if (header) {
      (header as HTMLElement).style.display = '';
    }

    // Remover clase del body
    document.body.classList.remove('kiosk-mode-active');
  }

  /**
   * Prevenir el clic derecho en modo kiosko
   */
  @HostListener('contextmenu', ['$event'])
  onRightClick(event: Event): void {
    if (this.isKioskMode) {
      event.preventDefault();
      return;
    }
  }

  /**
   * Prevenir F11 y otras teclas en modo kiosko
   */
  @HostListener('window:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    if (this.isKioskMode) {
      // Bloquear F11, F12, Esc, etc.
      if (event.key === 'F11' || event.key === 'F12' || event.key === 'Escape') {
        event.preventDefault();
      }

      // Bloquear Ctrl+teclas
      if (event.ctrlKey && ['a', 'c', 'v', 'x', 'w'].includes(event.key.toLowerCase())) {
        event.preventDefault();
      }
    }
  }



  /**
   * Carga los tipos de servicio disponibles
   */
  loadServiceTypes(): void {
    this.ticketService.getServiceTypes(true)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (types) => {
          this.serviceTypes = types;
          if (types.length === 0) {
            this.showMessage('No hay servicios disponibles en este momento', 'warning');
          }
        },
        error: (error) => {
          console.error('Error loading service types:', error);
          this.showMessage('Error al cargar los tipos de servicio', 'error');
        }
      });
  }

  /**
   * Busca un paciente por número de documento
   */
  searchPatient(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }

    const documentNumber = this.searchForm.get('documentNumber')?.value;
    this.isSearching = true;
    this.resetState();

    this.ticketService.searchPatientByDocument(documentNumber)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (patient) => {
          this.isSearching = false;
          this.currentPatient = patient;
          this.showPatientForm = false;
          this.showMessage(`Paciente encontrado: ${patient.FullName}`, 'success');
        },
        error: (error) => {
          this.isSearching = false;
          if (error.status === 404) {
            this.showNewPatientForm(documentNumber);
          } else {
            this.showMessage('Error al buscar el paciente', 'error');
          }
        }
      });
  }

  /**
   * Muestra el formulario para registrar un nuevo paciente
   */
  showNewPatientForm(documentNumber: string): void {
    this.showPatientForm = true;
    this.currentPatient = null;
    this.patientForm.patchValue({ documentNumber });
    this.showMessage('Paciente no registrado. Por favor complete los datos.', 'info');
  }

  /**
   * Registra un nuevo paciente
   */
  /**
   * Registra un nuevo paciente
   */
  registerPatient(): void {
    if (this.patientForm.invalid) {
      this.patientForm.markAllAsTouched();
      return;
    }

    const documentNumber = this.searchForm.get('documentNumber')?.value;
    const patientData: PatientCreate = {
      document_number: documentNumber,  // Cambiado a snake_case
      full_name: this.patientForm.get('fullName')?.value,
      birth_date: this.patientForm.get('birthDate')?.value,
      gender: this.patientForm.get('gender')?.value,
      phone: this.patientForm.get('phone')?.value || null,
      email: this.patientForm.get('email')?.value || null
    };

    this.isSearching = true;

    this.ticketService.createPatient(patientData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (patient) => {
          this.isSearching = false;
          this.currentPatient = patient;
          this.showPatientForm = false;
          this.showMessage('Paciente registrado exitosamente', 'success');
        },
        error: (error) => {
          this.isSearching = false;
          const errorMessage = error?.error?.detail || 'Error al registrar el paciente';
          this.showMessage(errorMessage, 'error');
        }
      });
  }
  /**
   * Selecciona un servicio y genera el ticket
   */
  /**
   * Selecciona un servicio y genera el ticket
   */
  selectService(serviceType: ServiceType): void {
    if (!this.currentPatient?.Id) {
      this.showMessage('Debe seleccionar un paciente primero', 'error');
      return;
    }

    console.log('Paciente actual:', this.currentPatient);
    console.log('Servicio seleccionado:', serviceType);

    this.isCreatingTicket = true;
    this.selectedServiceType = serviceType;

    // Llamar al servicio con los parámetros correctos
    this.ticketService.createQuickTicket(
      this.currentPatient.Id,  // ID del paciente
      serviceType.Id          // ID del tipo de servicio
    )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (ticket) => {
          this.isCreatingTicket = false;
          // Enriquecer el ticket con información adicional
          this.generatedTicket = {
            ...ticket,
            PatientName: this.generatedTicket?.PatientName || this.currentPatient!.FullName,
            PatientDocument: this.generatedTicket?.PatientDocument || this.currentPatient!.DocumentNumber,
            ServiceTypeName: this.generatedTicket?.ServiceTypeName || serviceType.Name,
            EstimatedTime: this.generatedTicket?.EstimatedTime || serviceType.AverageTimeMinutes
          };
          this.showMessage('Ticket generado exitosamente', 'success');
        },
        error: (error) => {
          this.isCreatingTicket = false;
          const errorMessage = error?.error?.detail || 'Error al generar el ticket';
          this.showMessage(errorMessage, 'error');
          console.error('Error al crear ticket:', error);
        }
      });
  }

  /**
   * Imprime el ticket generado
   */
  printTicket(): void {
    if (!this.generatedTicket || !this.currentPatient || !this.selectedServiceType) {
      this.showMessage('No hay ticket para imprimir', 'error');
      return;
    }

    try {
      this.ticketService.printTicket(
        this.generatedTicket,
        this.currentPatient,
        this.selectedServiceType
      );
      this.showMessage('Ticket enviado a imprimir', 'success');
    } catch (error) {
      console.error('Error al imprimir:', error);
      this.showMessage('Error al imprimir el ticket', 'error');
    }
  }

  /**
   * Cierra el diálogo del ticket y reinicia el componente
   */
  closeTicketDialog(): void {
    this.generatedTicket = null;
    this.resetState();
    this.searchForm.reset();
  }

  /**
   * Reinicia el estado del componente
   */
  resetState(): void {
    this.currentPatient = null;
    this.showPatientForm = false;
    this.generatedTicket = null;
    this.selectedServiceType = null;
    this.patientForm.reset();
  }

  /**
   * Cancela el registro de paciente
   */
  cancelRegistration(): void {
    this.showPatientForm = false;
    this.patientForm.reset();
    this.searchForm.reset();
  }

  /**
   * Inicia una nueva búsqueda
   */
  newSearch(): void {
    this.resetState();
    this.searchForm.reset();
  }

  /**
   * Obtiene la fecha máxima para el datepicker
   */
  getMaxDate(): string {
    return new Date().toISOString().split('T')[0];
  }

  /**
   * Obtiene la fecha mínima para el datepicker
   */
  getMinDate(): string {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 120);
    return date.toISOString().split('T')[0];
  }

  /**
   * Obtiene el icono correspondiente al servicio
   */
  getServiceIcon(serviceName: string): string {
    const iconMap: { [key: string]: string } = {
      'ENTREGA RESULTADOS': 'assignment',
      'LABORATORIO CLINICO': 'biotech',
      'TOMA MUESTRAS': 'vaccines',
      'RAYOS X': 'radio_button_checked',
      'ANALISIS SANGRE': 'bloodtype',
      'EXAMEN ORINA': 'science',
      'CONSULTA MEDICA': 'medical_services',
      'EMERGENCIA': 'emergency',
      'FARMACIA': 'local_pharmacy',
      'VACUNACION': 'vaccines'
    };

    return iconMap[serviceName.toUpperCase()] || 'medical_services';
  }

  /**
   * Muestra un mensaje al usuario
   */
  private showMessage(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: type === 'error' ? 5000 : 3000,
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
      panelClass: [`snackbar-${type}`]
    });
  }

  /**
   * Solicitar salida del modo kiosko (requiere contraseña)
   */
  exitKioskRequest(): void {
    const password = prompt('Ingrese la contraseña de administrador:');
    if (password === 'admin123') { // Cambiar por validación real
      this.isKioskMode = false;
      this.exitKioskMode();
      // Navegar a otra página si es necesario
      // this.router.navigate(['/dashboard']);
    } else if (password) {
      this.showMessage('Contraseña incorrecta', 'error');
    }
  }

  /**
   * Actualiza el número de documento desde el teclado virtual
   */
  updateDocumentNumber(value: string): void {
    this.searchForm.patchValue({ documentNumber: value });
  }

  /**
   * Busca paciente usando el valor del teclado virtual
   */
  searchPatientWithKeyboard(documentNumber: string): void {
    this.searchForm.patchValue({ documentNumber });
    this.searchPatient();
  }

  addNumber(num: string): void {
    const currentValue = this.searchForm.get('documentNumber')?.value || '';
    if (currentValue.length < 20) { // Máximo 20 dígitos
      this.searchForm.patchValue({
        documentNumber: currentValue + num
      });
    }
  }

  /**
   * Borra el último dígito
   */
  backspace(): void {
    const currentValue = this.searchForm.get('documentNumber')?.value || '';
    if (currentValue.length > 0) {
      this.searchForm.patchValue({
        documentNumber: currentValue.slice(0, -1)
      });
    }
  }

  /**
   * Limpia todo el campo
   */
  clearNumber(): void {
    this.searchForm.patchValue({
      documentNumber: ''
    });
  }
}
