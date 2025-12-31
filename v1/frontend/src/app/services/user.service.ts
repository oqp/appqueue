// user.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../environments/environments';

// Interfaces matching backend schemas
export interface UserCreate {
  Username: string;
  Email: string;
  Password: string;
  FullName: string;
  RoleId: number;
  StationId?: number;
  IsActive?: boolean;
}

export interface UserUpdate {
  Email?: string;
  FullName?: string;
  RoleId?: number;
  StationId?: number | null;
  IsActive?: boolean;
}

export interface UserResponse {
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
  permissions?: string[];
  is_admin?: boolean;
  is_supervisor?: boolean;
  is_agente?: boolean;
  can_attend_patients?: boolean;
  days_since_last_login?: number;
  is_recently_active?: boolean;
}

export interface UserListResponse {
  users: UserResponse[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

export interface UserStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  users_by_role: { [key: string]: number };
  users_with_stations: number;
  users_without_stations: number;
  recent_logins_7d: number;
  recent_logins_30d: number;
  last_updated: Date;
}

export interface Role {
  Id: number;
  Name: string;
  Description?: string;
  IsActive: boolean;
}

export interface Station {
  Id: number;
  Name: string;
  Code: string;
  IsActive: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
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

  // ========== User CRUD Operations ==========

  /**
   * Get all users with optional filters
   */
  getUsers(filters?: {
    skip?: number;
    limit?: number;
    search?: string;
    role_id?: number;
    station_id?: number;
    is_active?: boolean;
    sort_by?: string;
    sort_desc?: boolean;
  }): Observable<UserListResponse> {
    let params = new HttpParams();

    if (filters) {
      if (filters.skip !== undefined) params = params.set('skip', filters.skip.toString());
      if (filters.limit !== undefined) params = params.set('limit', filters.limit.toString());
      if (filters.search) params = params.set('search', filters.search);
      if (filters.role_id !== undefined) params = params.set('role_id', filters.role_id.toString());
      if (filters.station_id !== undefined) params = params.set('station_id', filters.station_id.toString());
      if (filters.is_active !== undefined) params = params.set('is_active', filters.is_active.toString());
      if (filters.sort_by) params = params.set('sort_by', filters.sort_by);
      if (filters.sort_desc !== undefined) params = params.set('sort_desc', filters.sort_desc.toString());
    }

    return this.http.get<UserListResponse>(
      `${this.apiUrl}/users`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Search users
   */
  searchUsers(query: string, limit: number = 20): Observable<UserResponse[]> {
    const params = new HttpParams()
      .set('q', query)
      .set('limit', limit.toString());

    return this.http.get<UserResponse[]>(
      `${this.apiUrl}/users/search`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get user statistics
   */
  getUserStats(): Observable<UserStats> {
    return this.http.get<UserStats>(
      `${this.apiUrl}/users/stats`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get user by ID
   */
  getUser(id: string): Observable<UserResponse> {
    return this.http.get<UserResponse>(
      `${this.apiUrl}/users/${id}`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Create new user
   */
  createUser(user: UserCreate, autoGeneratePassword: boolean = false): Observable<UserResponse> {
    const params = new HttpParams()
      .set('auto_generate_password', autoGeneratePassword.toString())
      .set('send_welcome_email', 'false');

    return this.http.post<UserResponse>(
      `${this.apiUrl}/users`,
      user,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update user
   */
  updateUser(id: string, user: UserUpdate): Observable<UserResponse> {
    return this.http.put<UserResponse>(
      `${this.apiUrl}/users/${id}`,
      user,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete/Deactivate user
   */
  deleteUser(id: string, softDelete: boolean = true): Observable<any> {
    const params = new HttpParams().set('soft_delete', softDelete.toString());

    return this.http.delete(
      `${this.apiUrl}/users/${id}`,
      {
        headers: this.getAuthHeaders(),
        params
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Assign station to user
   */
  assignStation(userId: string, stationId: number | null, reason?: string): Observable<any> {
    return this.http.put(
      `${this.apiUrl}/users/${userId}/assign-station`,
      {
        station_id: stationId,
        reason: reason
      },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Assign role to user
   */
  assignRole(userId: string, roleId: number, reason?: string): Observable<any> {
    return this.http.put(
      `${this.apiUrl}/users/${userId}/assign-role`,
      {
        role_id: roleId,
        reason: reason
      },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Change user password
   */
  changePassword(userId: string, currentPassword: string, newPassword: string): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/users/${userId}/change-password`,
      {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: newPassword
      },
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  // ========== Roles & Stations ==========

  /**
   * Get all roles
   */
  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(
      `${this.apiUrl}/admin/roles`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get all stations for assignment
   */
  getStations(): Observable<Station[]> {
    return this.http.get<any>(
      `${this.apiUrl}/stations`,
      { headers: this.getAuthHeaders() }
    ).pipe(
      catchError(this.handleError)
    );
  }
}
