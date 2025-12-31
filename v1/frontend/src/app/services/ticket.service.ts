import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../environments/environments';

// Interfaces para el Frontend (PascalCase)
export interface Patient {
  Id?: string;
  DocumentNumber: string;
  FullName: string;
  BirthDate: string;
  Gender: 'M' | 'F' | 'Otro';
  Phone?: string;
  Email?: string;
  Age?: number;
  IsActive?: boolean;
  CreatedAt?: string;
  UpdatedAt?: string;
}

// Interface para la respuesta del Backend (snake_case)
export interface PatientBackendResponse {
  id?: string;
  document_type?: string;
  document_number: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  birth_date: string;
  gender: string;
  email?: string;
  phone?: string;
  age?: number;
  is_active?: boolean;
  CreatedAt?: string;
  UpdatedAt?: string;
}

export interface ServiceType {
  Id: number;
  Code: string;
  Name: string;
  Description?: string;
  Priority: number;
  AverageTimeMinutes: number;
  TicketPrefix: string;
  Color?: string;
  IsActive: boolean;
  CreatedAt?: string;
  UpdatedAt?: string;
}

export interface ServiceTypeListResponse {
  services?: ServiceType[];
  data?: ServiceType[];
  items?: ServiceType[];
  ServiceTypes?: ServiceType[];
  total?: number;
  count?: number;
}

export interface Ticket {
  Id: string;
  TicketNumber: string;
  Code: string;
  PatientId: string;
  PatientName?: string;
  PatientDocument?: string;
  ServiceTypeId: number;
  ServiceTypeName?: string;
  EstimatedTime?: number;
  CreatedAt: string;
  Status: string;
  Priority?: number;
  StationId?: number;
  StationName?: string;
  CalledAt?: string;
  AttendedAt?: string;
  CompletedAt?: string;
}

export interface TicketCreate {
  PatientId: string;
  ServiceTypeId: number;
  StationId?: number;
  Notes?: string;
}

export interface TicketQuickCreate {
  PatientDocumentNumber: string;
  ServiceTypeId: number;
  Notes?: string;
}

export interface PatientCreate {
  document_number: string;
  first_name: string;
  last_name: string;
  birth_date?: string;
  gender: 'M' | 'F' | 'Otro';
  phone?: string | null;
  email?: string | null;
}

export interface TicketListResponse {
  tickets: Ticket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PrintData {
  turno: string;
  servicio: string;
  dni: string;
  nombre: string;
  codigo_orden: string;
  tiempo_estimado: number;
  fecha_hora: string;
}

@Injectable({
  providedIn: 'root'
})
export class TicketService {
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {}

  // ========== Helper Methods ==========

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  private handleError(error: any): Observable<never> {
    console.error('API Error:', error);
    return throwError(() => error);
  }

  /**
   * Mapea la respuesta del backend al formato del frontend
   */
  private mapPatientFromBackend(backendPatient: PatientBackendResponse): Patient {
    return {
      Id: backendPatient.id,
      DocumentNumber: backendPatient.document_number,
      FullName: backendPatient.full_name,
      BirthDate: backendPatient.birth_date,
      Gender: backendPatient.gender as 'M' | 'F' | 'Otro',
      Phone: backendPatient.phone || undefined,
      Email: backendPatient.email || undefined,
      Age: backendPatient.age,
      IsActive: backendPatient.is_active !== undefined ? backendPatient.is_active : true,
      CreatedAt: backendPatient.CreatedAt,
      UpdatedAt: backendPatient.UpdatedAt
    };
  }

  /**
   * Mapea los datos del frontend al formato del backend
   */
  private mapPatientToBackend(patient: PatientCreate): any {
    return {
      document_number: patient.document_number,
      first_name: patient.first_name,
      last_name: patient.last_name,
      birth_date: patient.birth_date || null,
      gender: patient.gender,
      phone: patient.phone || null,
      email: patient.email || null
    };
  }

  // ========== Patient Operations ==========

  /**
   * Busca un paciente por número de documento
   */
  searchPatientByDocument(documentNumber: string): Observable<Patient> {
    console.log('Buscando paciente con documento:', documentNumber);

    return this.http.get<PatientBackendResponse>(
      `${this.apiUrl}/patients/document/${documentNumber}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        console.log('Respuesta del backend (paciente):', response);
        const mappedPatient = this.mapPatientFromBackend(response);
        console.log('Paciente mapeado:', mappedPatient);
        return mappedPatient;
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Crea un nuevo paciente
   */
  createPatient(patient: PatientCreate): Observable<Patient> {
    console.log('Creando paciente:', patient);

    const backendData = this.mapPatientToBackend(patient);
    console.log('Datos enviados al backend:', backendData);

    return this.http.post<PatientBackendResponse>(
      `${this.apiUrl}/patients`,
      backendData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        console.log('Respuesta del backend (crear paciente):', response);
        return this.mapPatientFromBackend(response);
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Obtiene la lista de pacientes
   */
  getPatients(skip: number = 0, limit: number = 100, search?: string): Observable<Patient[]> {
    let url = `${this.apiUrl}/patients?skip=${skip}&limit=${limit}`;
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }

    return this.http.get<PatientBackendResponse[]>(url, { headers: this.getAuthHeaders() })
      .pipe(
        map(patients => patients.map(p => this.mapPatientFromBackend(p))),
        catchError(this.handleError)
      );
  }

  /**
   * Actualiza un paciente
   */
  updatePatient(patientId: string, patient: Partial<Patient>): Observable<Patient> {
    const backendData: any = {};

    // Mapear solo los campos que se van a actualizar
    if (patient.FullName !== undefined) backendData.full_name = patient.FullName;
    if (patient.BirthDate !== undefined) backendData.birth_date = patient.BirthDate;
    if (patient.Gender !== undefined) backendData.gender = patient.Gender;
    if (patient.Phone !== undefined) backendData.phone = patient.Phone;
    if (patient.Email !== undefined) backendData.email = patient.Email;

    return this.http.put<PatientBackendResponse>(
      `${this.apiUrl}/patients/${patientId}`,
      backendData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => this.mapPatientFromBackend(response)),
      catchError(this.handleError)
    );
  }

  // ========== Service Type Operations ==========

  /**
   * Obtiene todos los tipos de servicio activos
   */
  getServiceTypes(activeOnly: boolean = true): Observable<ServiceType[]> {
    const url = `${this.apiUrl}/service-types${activeOnly ? '?active_only=true' : ''}`;

    return this.http.get<ServiceType[] | ServiceTypeListResponse>(url, { headers: this.getAuthHeaders() })
      .pipe(
        map(response => {
          console.log('Response from service-types:', response);

          // Si la respuesta es un array directo
          if (Array.isArray(response)) {
            return activeOnly ? response.filter(t => t.IsActive) : response;
          }

          // Si la respuesta es un objeto con una propiedad que contiene el array
          const possibleArrayProps = ['services', 'data', 'items', 'ServiceTypes', 'service_types', 'results'];

          for (const prop of possibleArrayProps) {
            if (response[prop as keyof ServiceTypeListResponse] && Array.isArray(response[prop as keyof ServiceTypeListResponse])) {
              const types = response[prop as keyof ServiceTypeListResponse] as ServiceType[];
              return activeOnly ? types.filter(t => t.IsActive) : types;
            }
          }

          console.warn('No se pudo encontrar el array de ServiceTypes en la respuesta:', response);
          return [];
        }),
        catchError((error) => {
          console.error('Error loading service types:', error);
          // No usar mock data - mostrar error real al usuario
          return throwError(() => error);
        })
      );
  }

  /**
   * Obtiene un tipo de servicio por ID
   */
  getServiceTypeById(id: number): Observable<ServiceType> {
    return this.http.get<ServiceType>(
      `${this.apiUrl}/service-types/${id}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Ticket Operations ==========

  /**
   * Crea un ticket rápido
   */
  /**
   * Crea un ticket usando el endpoint regular /tickets
   * (El endpoint /quick requiere documento, pero ya tenemos el ID del paciente)
   */
  createQuickTicket(patientId: string, serviceTypeId: number): Observable<Ticket> {
    console.log('Creando ticket para paciente:', patientId, 'servicio:', serviceTypeId);

    // Usar el endpoint regular /tickets que espera PatientId
    const ticketData: TicketCreate = {
      PatientId: patientId,  // El backend espera PascalCase
      ServiceTypeId: serviceTypeId,
      Notes: 'Ticket generado desde kiosko de autoatención'
    };

    console.log('Datos enviados al backend:', ticketData);

    return this.http.post<any>(
      `${this.apiUrl}/tickets`,  // Usar endpoint regular, no /quick
      ticketData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        console.log('Respuesta del backend (ticket creado):', response);

        // Mapear la respuesta del backend al formato del frontend
        return {
          Id: response.Id || response.id,
          TicketNumber: response.TicketNumber || response.ticket_number,
          Code: response.Code || response.code || response.QrCode || response.qr_code,
          PatientId: response.PatientId || response.patient_id,
          PatientName: response.PatientName || response.patient_name,
          PatientDocument: response.PatientDocument || response.patient_document,
          ServiceTypeId: response.ServiceTypeId || response.service_type_id,
          ServiceTypeName: response.ServiceTypeName || response.service_type_name,
          EstimatedTime: response.EstimatedTime || response.estimated_time || response.EstimatedWaitTime,
          CreatedAt: response.CreatedAt || response.created_at,
          Status: response.Status || response.status || 'WAITING',
          Priority: response.Priority || response.priority
        } as Ticket;
      }),
      catchError((error) => {
        console.error('Error completo del backend:', error);
        if (error.error && error.error.detail) {
          console.error('Detalle del error:', error.error.detail);
        }
        return this.handleError(error);
      })
    );
  }
  /**
   * Crea un ticket anónimo (sin paciente registrado)
   */
  createAnonymousTicket(serviceTypeId: number, documentNumber?: string): Observable<Ticket> {
    console.log('Creando ticket anónimo para servicio:', serviceTypeId);

    const ticketData = {
      ServiceTypeId: serviceTypeId,
      Notes: `Ticket anónimo - Documento: ${documentNumber || 'N/A'}`,
      IsAnonymous: true,
      DocumentNumber: documentNumber || null
    };

    console.log('Datos enviados al backend:', ticketData);

    return this.http.post<any>(
      `${this.apiUrl}/tickets/anonymous`,
      ticketData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        console.log('Respuesta del backend (ticket anónimo):', response);

        return {
          Id: response.Id || response.id,
          TicketNumber: response.TicketNumber || response.ticket_number,
          Code: response.Code || response.code || response.QrCode || response.qr_code,
          PatientId: response.PatientId || response.patient_id || '',
          PatientName: 'SIN REGISTRO',
          PatientDocument: documentNumber || 'N/A',
          ServiceTypeId: response.ServiceTypeId || response.service_type_id,
          ServiceTypeName: response.ServiceTypeName || response.service_type_name,
          EstimatedTime: response.EstimatedTime || response.estimated_time || response.EstimatedWaitTime,
          CreatedAt: response.CreatedAt || response.created_at,
          Status: response.Status || response.status || 'WAITING',
          Priority: response.Priority || response.priority
        } as Ticket;
      }),
      catchError((error) => {
        console.error('Error completo del backend:', error);
        return this.handleError(error);
      })
    );
  }

  /**
   * Crea un ticket completo
   */
  createTicket(ticket: Partial<Ticket>): Observable<Ticket> {
    const backendData: any = {
      patient_id: ticket.PatientId,
      service_type_id: ticket.ServiceTypeId,
      priority: ticket.Priority
    };

    return this.http.post<any>(
      `${this.apiUrl}/tickets`,
      backendData,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        return {
          Id: response.id || response.Id,
          TicketNumber: response.ticket_number || response.TicketNumber,
          Code: response.code || response.Code,
          PatientId: response.patient_id || response.PatientId,
          ServiceTypeId: response.service_type_id || response.ServiceTypeId,
          CreatedAt: response.created_at || response.CreatedAt,
          Status: response.status || response.Status || 'WAITING'
        } as Ticket;
      }),
      catchError(this.handleError)
    );
  }

  // ... resto de los métodos sin cambios ...

  /**
   * Imprime un ticket
   */
  /**
   * Imprime un ticket
   */
  printTicket(ticket: Ticket, patient: Patient, serviceType: ServiceType): void {
    const printData = {
      turno: ticket.TicketNumber,
      servicio: serviceType.Name,
      dni: patient.DocumentNumber,
      nombre: patient.FullName,
      codigo_orden: ticket.TicketNumber // Usar TicketNumber si no hay Code
    };

    if (environment.printServiceUrl) {
      this.sendToPrintService(printData).subscribe({
        next: (success) => {
          if (success) {
            console.log('Ticket enviado al servicio de impresión exitosamente');
          }
        },
        error: (error) => {
          console.error('Error al enviar al servicio de impresión:', error);
          // Fallback a impresión del navegador
          this.printWithBrowser(printData);
        }
      });
    } else {
      // Si no hay servicio configurado, usar navegador
      this.printWithBrowser(printData);
    }
  }

  /**
   * Envía datos al servicio de impresión local
   */
  private sendToPrintService(printData: any): Observable<boolean> {
    const url = `${environment.printServiceUrl}/print-ticket`;

    console.log('Enviando a imprimir:', printData);
    console.log('URL del servicio:', url);

    // No necesitamos headers de autenticación para el servicio local
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });

    return this.http.post<any>(url, printData, { headers })
      .pipe(
        map(response => {
          console.log('Respuesta del servicio de impresión:', response);
          return true;
        }),
        catchError((error) => {
          console.error('Error al imprimir con servicio local:', error);
          // Si falla, intentar con el navegador
          this.printWithBrowser(printData);
          return of(false);
        })
      );
  }

  /**
   * Método de respaldo: Imprime usando el navegador
   */
  private printWithBrowser(printData: any): void {
    const printWindow = window.open('', '_blank', 'width=400,height=600');

    if (printWindow) {
      const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Ticket ${printData.turno}</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          body {
            font-family: 'Courier New', monospace;
            padding: 20px;
            text-align: center;
            font-size: 14px;
          }
          .header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
          }
          .divider {
            border-bottom: 2px dashed #000;
            margin: 10px 0;
          }
          .turno {
            font-size: 48px;
            font-weight: bold;
            margin: 20px 0;
            letter-spacing: 2px;
          }
          .info {
            text-align: left;
            margin: 10px 0;
          }
          .info-row {
            margin: 5px 0;
            font-size: 13px;
          }
          .footer {
            margin-top: 20px;
            font-size: 12px;
          }
          @media print {
            body {
              margin: 0;
              padding: 10px;
            }
            @page {
              margin: 0;
              size: 80mm;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          LABORATORIOS<br>
          MUÑOZ
        </div>
        <div class="divider"></div>

        <div style="font-size: 20px; margin: 10px 0; font-weight: bold;">
          ${printData.servicio}
        </div>

        <div style="margin: 15px 0; font-size: 16px;">
          SU TURNO ES:
        </div>
        <div class="turno">
          ${printData.turno}
        </div>

        <div class="divider"></div>

        <div class="info">
          <div class="info-row"><strong>PACIENTE:</strong></div>
          <div class="info-row">DNI: ${printData.dni}</div>
          <div class="info-row">${printData.nombre}</div>
        </div>

        <div class="divider"></div>

        <div class="info">
          <div class="info-row">FECHA: ${new Date().toLocaleDateString('es-PE')}</div>
          <div class="info-row">HORA: ${new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>

        <div class="divider"></div>

        <div style="margin: 15px 0;">
          <div style="font-size: 14px;"><strong>CÓDIGO: ${printData.codigo_orden}</strong></div>
        </div>

        <div class="divider"></div>

        <div class="footer">
          Por favor espere su turno<br>
          en la sala de espera<br><br>
          <strong>GRACIAS POR SU PREFERENCIA</strong><br><br>
          Impreso: ${new Date().toLocaleString('es-PE')}
        </div>
      </body>
      </html>
    `;

      printWindow.document.write(htmlContent);
      printWindow.document.close();

      setTimeout(() => {
        printWindow.print();
        printWindow.onafterprint = () => printWindow.close();
      }, 250);
    } else {
      alert('No se pudo abrir la ventana de impresión. Por favor, verifique los permisos del navegador.');
    }
  }

}
