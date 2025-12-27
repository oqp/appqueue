// queue.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { map, catchError, tap } from 'rxjs/operators';
import {environment} from '../environments/environments';

// Interfaces
export interface QueueState {
  Id: number;
  ServiceTypeId: number;
  ServiceName?: string;
  ServiceCode?: string;
  StationId?: number;
  StationName?: string;
  StationCode?: string;
  CurrentTicketId?: string;
  CurrentTicketNumber?: string;
  NextTicketId?: string;
  NextTicketNumber?: string;
  QueueLength: number;
  AverageWaitTime: number;
  LastUpdateAt: Date;
  IsActive: boolean;
  EstimatedWaitTime?: number;
  Color?: string;
  TicketPrefix?: string;
  PendingTickets?: any[];
}

export interface QueueSummary {
  TotalQueues: number;
  ActiveQueues: number;
  TotalWaiting: number;
  StationsBusy: number;
  AverageWaitTime: number;
}

export interface AdvanceQueueRequest {
  ServiceTypeId: number;
  StationId?: number;
  MarkCompleted?: boolean;
}

export interface ResetQueueRequest {
  ServiceTypeId: number;
  StationId?: number;
  Reason: string;
  CancelPendingTickets?: boolean;
}

export interface UpdateWaitTimeRequest {
  QueueStateId: number;
  Recalculate?: boolean;
  ManualTime?: number;
}

export interface ServiceType {
  Id: number;
  Name: string;
  Code: string;
  Color: string;
  TicketPrefix: string;
  Priority: number;
  AverageTimeMinutes: number;
  IsActive: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class QueueService {
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {}

  // Helper method to get auth headers
  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  // Get all queue states
  getQueueStates(activeOnly: boolean = false): Observable<QueueState[]> {
    const params = new HttpParams()
      .set('active_only', activeOnly.toString());

    return this.http.get<QueueState[]>(
      `${this.apiUrl}/queue-states/`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      map(response => {
        console.log('Queue states response:', response);

        // Handle response structure variations
        if (Array.isArray(response)) {
          return response;
        }
        // If response is wrapped in an object
        if (response && typeof response === 'object') {
          const possibleKeys = ['queues', 'data', 'items', 'queue_states'];
          for (const key of possibleKeys) {
            if (response[key as keyof typeof response] && Array.isArray(response[key as keyof typeof response])) {
              return response[key as keyof typeof response] as QueueState[];
            }
          }
        }
        return [];
      }),
      catchError((error) => {
        console.error('Error loading queue states:', error);

        // Si no hay datos, intentar inicializar las colas
        if (error.status === 404 || (error.status === 200 && (!error.error || error.error.length === 0))) {
          console.log('No queue states found, attempting to initialize...');
          return this.initializeQueues();
        }

        return this.handleError(error);
      })
    );
  }

  // Initialize queue states from existing tickets
  private initializeQueues(): Observable<QueueState[]> {
    return this.http.post<any>(
      `${this.apiUrl}/queue-states/initialize`,
      {},
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(() => {
        console.log('Queues initialized, reloading...');
        // After initialization, try to get the states again
        return [];
      }),
      catchError(() => {
        // If initialization endpoint doesn't exist, return empty array
        console.log('Queue initialization endpoint not available');
        return of([]);
      })
    );
  }

  // Get queue summary
  getQueueSummary(): Observable<QueueSummary> {
    return this.http.get<QueueSummary>(
      `${this.apiUrl}/queue-states/summary`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // Get active queues with tickets
  getActiveQueues(): Observable<QueueState[]> {
    return this.http.get<QueueState[]>(
      `${this.apiUrl}/queue-states/active/all`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => Array.isArray(response) ? response : []),
      catchError(this.handleError)
    );
  }

  // Get queue by ID
  getQueueById(id: number): Observable<QueueState> {
    return this.http.get<QueueState>(
      `${this.apiUrl}/queue-states/${id}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // Advance queue
  advanceQueue(serviceTypeId: number, stationId?: number): Observable<any> {
    const request: AdvanceQueueRequest = {
      ServiceTypeId: serviceTypeId,
      StationId: stationId,
      MarkCompleted: true
    };

    return this.http.post<any>(
      `${this.apiUrl}/queue-states/advance`,
      request,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap(() => console.log('Queue advanced successfully')),
      catchError(this.handleError)
    );
  }

  // Reset queue
  resetQueue(serviceTypeId: number, stationId: number | undefined, reason: string): Observable<any> {
    const request: ResetQueueRequest = {
      ServiceTypeId: serviceTypeId,
      StationId: stationId,
      Reason: reason,
      CancelPendingTickets: false
    };

    return this.http.post<any>(
      `${this.apiUrl}/queue-states/reset`,
      request,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap(() => console.log('Queue reset successfully')),
      catchError(this.handleError)
    );
  }

  // Update wait time
  updateWaitTime(queueId: number, manualTime: number): Observable<any> {
    const request: UpdateWaitTimeRequest = {
      QueueStateId: queueId,
      Recalculate: false,
      ManualTime: manualTime
    };

    return this.http.patch<any>(
      `${this.apiUrl}/queue-states/${queueId}/wait-time`,
      request,
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap(() => console.log('Wait time updated successfully')),
      catchError(this.handleError)
    );
  }

  // Initialize all queue states
  initializeAllQueues(): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/queue-states/initialize-all`,
      {},
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap(result => console.log('Initialize result:', result)),
      catchError((error) => {
        console.error('Initialize error:', error);
        return throwError(() => error);
      })
    );
  }

  // Check consistency
  checkConsistency(fix: boolean = false): Observable<any> {
    const params = new HttpParams().set('fix_issues', fix.toString());

    return this.http.get<any>(
      `${this.apiUrl}/queue-states/consistency-check`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      tap(result => console.log('Consistency check:', result)),
      catchError((error) => {
        console.error('Consistency check error:', error);
        return of({ is_consistent: false, message: 'Error checking consistency' });
      })
    );
  }

  // Refresh all queues
  refreshAllQueues(): Observable<any> {
    return this.http.post<any>(
      `${this.apiUrl}/queue-states/refresh-all`,
      {},
      { headers: this.getAuthHeaders() }
    ).pipe(
      tap(result => console.log('Refresh result:', result)),
      catchError((error) => {
        console.error('Refresh error:', error);
        return throwError(() => error);
      })
    );
  }

  // Get service types (for filters)
  getServiceTypes(): Observable<ServiceType[]> {
    return this.http.get<ServiceType[]>(
      `${this.apiUrl}/service-types/`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      map(response => {
        if (Array.isArray(response)) {
          return response.filter(s => s.IsActive);
        }
        return [];
      }),
      catchError(() => {
        // Return mock data if API fails
        return of([
          {
            Id: 1,
            Name: 'Análisis de Sangre',
            Code: 'LAB',
            Color: '#4477ff',
            TicketPrefix: 'A',
            Priority: 1,
            AverageTimeMinutes: 15,
            IsActive: true
          },
          {
            Id: 2,
            Name: 'Rayos X',
            Code: 'RAD',
            Color: '#22c55e',
            TicketPrefix: 'R',
            Priority: 2,
            AverageTimeMinutes: 20,
            IsActive: true
          }
        ]);
      })
    );
  }

  // Error handler
  private handleError(error: any): Observable<never> {
    console.error('Queue service error:', error);

    let errorMessage = 'Ocurrió un error en el servicio de colas';

    if (error.error?.detail) {
      errorMessage = error.error.detail;
    } else if (error.status === 401) {
      errorMessage = 'No autorizado. Por favor inicie sesión nuevamente.';
    } else if (error.status === 403) {
      errorMessage = 'No tiene permisos para realizar esta acción.';
    } else if (error.status === 404) {
      errorMessage = 'Recurso no encontrado.';
    } else if (error.status === 500) {
      errorMessage = 'Error del servidor. Por favor intente más tarde.';
    }

    return throwError(() => new Error(errorMessage));
  }
}
