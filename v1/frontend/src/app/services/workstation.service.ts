// workstation.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {environment} from '../environments/environments';


// Interfaces matching backend schemas
interface StationCreate {
  Name: string;
  Code: string;
  Description?: string;
  ServiceTypeId?: number;
  Location?: string;
  Status?: string;
  IsActive?: boolean;
}

interface StationUpdate {
  Name?: string;
  Description?: string;
  ServiceTypeId?: number;
  Location?: string;
  Status?: string;
  IsActive?: boolean;
}

interface StationResponse {
  Id: number;
  Name: string;
  Code: string;
  Description?: string;
  ServiceTypeId?: number;
  ServiceTypeName?: string;
  Location?: string;
  Status: string;
  CurrentTicketId?: string;
  CurrentTicketNumber?: string;
  IsActive: boolean;
  CreatedAt: Date;
  UpdatedAt?: Date;
  AssignedUsers?: any[];
  QueueLength?: number;
}

interface StationListResponse {
  Stations: StationResponse[];
  Total: number;
  Page: number;
  PageSize: number;
  TotalPages: number;
  HasNext: boolean;
  HasPrev: boolean;
}

interface ServiceType {
  Id: number;
  Code: string;
  Name: string;
  Description?: string;
  Priority: number;
  AverageTimeMinutes: number;
  TicketPrefix: string;
  Color?: string;
  IsActive: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class WorkstationService {
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {}

  // ========== Helper Methods ==========

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  private handleError(error: any): Observable<never> {
    console.error('API Error:', error);
    const errorMessage = error?.error?.detail || error?.message || 'Error desconocido';
    return throwError(() => new Error(errorMessage));
  }

  // ========== Station CRUD Operations ==========

  /**
   * Get all stations with optional filters
   */
  getStations(filters?: any): Observable<StationListResponse | StationResponse[]> {
    let params = new HttpParams();

    if (filters) {
      if (filters.search) {
        params = params.set('query', filters.search);
      }
      if (filters.status) {
        params = params.set('status', filters.status);
      }
      if (filters.serviceType) {
        params = params.set('service_type_id', filters.serviceType);
      }
      if (filters.onlyActive !== undefined) {
        params = params.set('only_active', filters.onlyActive);
      }
    }

    return this.http.get<StationListResponse | StationResponse[]>(
      `${this.apiUrl}/stations`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get available stations
   */
  getAvailableStations(serviceTypeId?: number): Observable<StationResponse[]> {
    let params = new HttpParams();

    if (serviceTypeId) {
      params = params.set('service_type_id', serviceTypeId);
    }

    return this.http.get<StationResponse[]>(
      `${this.apiUrl}/stations/available`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get station by ID
   */
  getStation(id: number): Observable<StationResponse> {
    return this.http.get<StationResponse>(
      `${this.apiUrl}/stations/${id}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get station by code
   */
  getStationByCode(code: string): Observable<StationResponse> {
    return this.http.get<StationResponse>(
      `${this.apiUrl}/stations/by-code/${code}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Create new station
   */
  createStation(station: StationCreate): Observable<StationResponse> {
    return this.http.post<StationResponse>(
      `${this.apiUrl}/stations`,
      station,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update station
   */
  updateStation(id: number, station: StationUpdate): Observable<StationResponse> {
    return this.http.put<StationResponse>(
      `${this.apiUrl}/stations/${id}`,
      station,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update station status
   */
  updateStationStatus(id: number, status: string): Observable<StationResponse> {
    return this.http.patch<StationResponse>(
      `${this.apiUrl}/stations/${id}/status`,
      { status },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete station
   */
  deleteStation(id: number, softDelete: boolean = true): Observable<any> {
    const params = new HttpParams().set('soft_delete', softDelete.toString());

    return this.http.delete(
      `${this.apiUrl}/stations/${id}`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Service Types ==========

  /**
   * Get all service types
   */
  getServiceTypes(): Observable<ServiceType[]> {
    return this.http.get<ServiceType[]>(
      `${this.apiUrl}/service-types`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Station Assignment Operations ==========

  /**
   * Assign user to station
   */
  assignUserToStation(stationId: number, userId: string, notes?: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/stations/${stationId}/assign-user`,
      {
        UserId: userId,
        Notes: notes
      },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Remove user from station
   */
  removeUserFromStation(stationId: number, userId: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/stations/${stationId}/remove-user`,
      { UserId: userId },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Queue Operations ==========

  /**
   * Get station queue
   */
  getStationQueue(stationId: number): Observable<any> {
    return this.http.get(
      `${this.apiUrl}/stations/${stationId}/queue`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Call next ticket in station
   */
  callNextTicket(stationId: number): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/stations/${stationId}/call-next`,
      {},
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Transfer patients between stations
   */
  transferPatients(sourceStationId: number, targetStationId: number, ticketIds?: string[]): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/stations/transfer-patients`,
      {
        SourceStationId: sourceStationId,
        TargetStationId: targetStationId,
        TicketIds: ticketIds,
        TransferAll: !ticketIds || ticketIds.length === 0
      },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Statistics & Reports ==========

  /**
   * Get station statistics
   */
  getStationStats(stationId: number): Observable<any> {
    return this.http.get(
      `${this.apiUrl}/stations/${stationId}/stats`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get station performance report
   */
  getStationPerformance(stationId: number, period?: string): Observable<any> {
    let params = new HttpParams();

    if (period) {
      params = params.set('period', period);
    }

    return this.http.get(
      `${this.apiUrl}/stations/${stationId}/performance`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }
}
