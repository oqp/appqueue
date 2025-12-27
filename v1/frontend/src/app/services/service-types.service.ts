import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {environment} from '../environments/environments';
import {ServiceType, ServiceTypeDashboard, ServiceTypeListResponse} from './service-type.model';


@Injectable({
  providedIn: 'root'
})
export class ServiceTypesService {
  private apiUrl = `${environment.apiUrl}/api/v1/service-types`;

  constructor(private http: HttpClient) { }

  // ========== Helper Methods ==========

  /**
   * Obtiene los headers con autorización
   */
  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Maneja errores de las peticiones HTTP
   */
  private handleError(error: any): Observable<never> {
    console.error('API Error:', error);
    const errorMessage = error?.error?.detail || error?.message || 'Error desconocido';
    return throwError(() => new Error(errorMessage));
  }

  // ========== Service Types CRUD Operations ==========

  /**
   * Obtiene la lista de tipos de servicios con paginación y filtros
   */
  getServiceTypes(
    skip: number = 0,
    limit: number = 20,
    activeOnly: boolean = true,
    priority?: number | null
  ): Observable<ServiceTypeListResponse> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString())
      .set('active_only', activeOnly.toString());

    if (priority !== null && priority !== undefined) {
      params = params.set('priority', priority.toString());
    }

    return this.http.get<ServiceTypeListResponse>(
      this.apiUrl,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Obtiene un tipo de servicio por ID
   */
  getServiceTypeById(id: number, includeStats: boolean = false): Observable<ServiceType> {
    const params = new HttpParams().set('include_stats', includeStats.toString());

    return this.http.get<ServiceType>(
      `${this.apiUrl}/${id}`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Obtiene un tipo de servicio por código
   */
  getServiceTypeByCode(code: string, includeStats: boolean = false): Observable<ServiceType> {
    const params = new HttpParams().set('include_stats', includeStats.toString());

    return this.http.get<ServiceType>(
      `${this.apiUrl}/code/${code}`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Crea un nuevo tipo de servicio
   */
  createServiceType(serviceType: Partial<ServiceType>): Observable<ServiceType> {
    return this.http.post<ServiceType>(
      this.apiUrl,
      serviceType,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Actualiza un tipo de servicio existente
   */
  updateServiceType(id: number, serviceType: Partial<ServiceType>): Observable<ServiceType> {
    return this.http.put<ServiceType>(
      `${this.apiUrl}/${id}`,
      serviceType,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Elimina un tipo de servicio (soft delete por defecto)
   */
  deleteServiceType(id: number, softDelete: boolean = true): Observable<any> {
    const params = new HttpParams().set('soft_delete', softDelete.toString());

    return this.http.delete(
      `${this.apiUrl}/${id}`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Advanced Operations ==========

  /**
   * Búsqueda avanzada de tipos de servicios
   */
  searchServiceTypes(filters: {
    search_text?: string;
    active_only?: boolean;
    priority?: number;
    min_time?: number;
    max_time?: number;
    has_stations?: boolean;
  }): Observable<ServiceType[]> {
    return this.http.post<ServiceType[]>(
      `${this.apiUrl}/search`,
      filters,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Obtiene el dashboard con estadísticas
   */
  getDashboard(): Observable<ServiceTypeDashboard> {
    return this.http.get<ServiceTypeDashboard>(
      `${this.apiUrl}/dashboard`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Configuración rápida de tipos de servicios
   */
  quickSetup(data: {
    include_default_services?: boolean;
    custom_services?: Partial<ServiceType>[];
  }): Observable<ServiceType[]> {
    return this.http.post<ServiceType[]>(
      `${this.apiUrl}/quick-setup`,
      data,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Creación masiva de tipos de servicios
   */
  bulkCreate(serviceTypes: Partial<ServiceType>[]): Observable<{
    created: ServiceType[];
    failed: any[];
    total_processed: number;
  }> {
    return this.http.post<any>(
      `${this.apiUrl}/bulk`,
      { service_types: serviceTypes },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Validation Operations ==========

  /**
   * Valida si un código está disponible
   */
  validateCode(code: string): Observable<{ available: boolean; message: string }> {
    return this.http.get<any>(
      `${this.apiUrl}/validate/code/${code}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Valida si un prefijo de ticket está disponible
   */
  validatePrefix(prefix: string): Observable<{ available: boolean; message: string }> {
    return this.http.get<any>(
      `${this.apiUrl}/validate/prefix/${prefix}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Statistics & Reports ==========

  /**
   * Obtiene estadísticas de un tipo de servicio específico
   */
  getServiceTypeStats(id: number): Observable<any> {
    return this.http.get(
      `${this.apiUrl}/${id}/stats`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Obtiene reporte de rendimiento
   */
  getServiceTypePerformance(id: number, period?: string): Observable<any> {
    let params = new HttpParams();

    if (period) {
      params = params.set('period', period);
    }

    return this.http.get(
      `${this.apiUrl}/${id}/performance`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }
}
