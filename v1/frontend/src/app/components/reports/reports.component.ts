import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { Subject } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environments';

interface DashboardStats {
  period: { from: string; to: string };
  tickets: {
    total: number;
    completed: number;
    cancelled: number;
    waiting: number;
    in_progress: number;
    completion_rate: number;
  };
  times: {
    avg_wait_minutes: number;
    avg_service_minutes: number;
    max_wait_minutes: number;
    min_wait_minutes: number;
  };
}

interface ServiceStats {
  service_id: number;
  service_name: string;
  service_code: string;
  color: string;
  total: number;
  completed: number;
  completion_rate: number;
  avg_wait_minutes: number;
  avg_service_minutes: number;
}

interface StationStats {
  station_id: number;
  station_name: string;
  station_code: string;
  total: number;
  completed: number;
  completion_rate: number;
  avg_service_minutes: number;
}

interface HourData {
  hour: number;
  total: number;
}

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTableModule,
    MatSelectModule
  ],
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit, OnDestroy {
  loading = false;

  // Filtros de fecha
  dateFrom: Date = new Date();
  dateTo: Date = new Date();

  // Datos
  dashboardStats: DashboardStats | null = null;
  serviceStats: ServiceStats[] = [];
  stationStats: StationStats[] = [];
  hourlyData: HourData[] = [];
  peakHour: { hour: string; tickets: number } | null = null;

  // Para gráficos
  maxServiceTotal = 0;
  maxStationTotal = 0;
  maxHourlyTotal = 0;

  private destroy$ = new Subject<void>();
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {
    // Establecer fecha desde hace 7 días
    this.dateFrom = new Date();
    this.dateFrom.setDate(this.dateFrom.getDate() - 7);
  }

  ngOnInit(): void {
    this.loadAllReports();
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

  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  loadAllReports(): void {
    this.loading = true;

    const dateFromStr = this.formatDate(this.dateFrom);
    const dateToStr = this.formatDate(this.dateTo);

    // Cargar todos los reportes en paralelo
    Promise.all([
      this.loadDashboard(dateFromStr, dateToStr),
      this.loadServiceStats(dateFromStr, dateToStr),
      this.loadStationStats(dateFromStr, dateToStr),
      this.loadHourlyStats()
    ]).finally(() => {
      this.loading = false;
    });
  }

  private async loadDashboard(dateFrom: string, dateTo: string): Promise<void> {
    try {
      const response = await this.http.get<DashboardStats>(
        `${this.apiUrl}/reports/dashboard?date_from=${dateFrom}&date_to=${dateTo}`,
        { headers: this.getAuthHeaders() }
      ).toPromise();

      this.dashboardStats = response || null;
    } catch (error) {
      console.error('Error loading dashboard:', error);
    }
  }

  private async loadServiceStats(dateFrom: string, dateTo: string): Promise<void> {
    try {
      const response = await this.http.get<{data: ServiceStats[]}>(
        `${this.apiUrl}/reports/by-service?date_from=${dateFrom}&date_to=${dateTo}`,
        { headers: this.getAuthHeaders() }
      ).toPromise();

      this.serviceStats = response?.data || [];
      this.maxServiceTotal = Math.max(...this.serviceStats.map(s => s.total), 1);
    } catch (error) {
      console.error('Error loading service stats:', error);
    }
  }

  private async loadStationStats(dateFrom: string, dateTo: string): Promise<void> {
    try {
      const response = await this.http.get<{data: StationStats[]}>(
        `${this.apiUrl}/reports/by-station?date_from=${dateFrom}&date_to=${dateTo}`,
        { headers: this.getAuthHeaders() }
      ).toPromise();

      this.stationStats = response?.data || [];
      this.maxStationTotal = Math.max(...this.stationStats.map(s => s.total), 1);
    } catch (error) {
      console.error('Error loading station stats:', error);
    }
  }

  private async loadHourlyStats(): Promise<void> {
    try {
      const response = await this.http.get<{data: HourData[], peak_hour: {hour: string, tickets: number}}>(
        `${this.apiUrl}/reports/tickets-by-hour`,
        { headers: this.getAuthHeaders() }
      ).toPromise();

      this.hourlyData = response?.data || [];
      this.peakHour = response?.peak_hour || null;
      this.maxHourlyTotal = Math.max(...this.hourlyData.map(h => h.total), 1);
    } catch (error) {
      console.error('Error loading hourly stats:', error);
    }
  }

  getBarWidth(value: number, max: number): number {
    return max > 0 ? (value / max) * 100 : 0;
  }

  getHourLabel(hour: number): string {
    return `${hour.toString().padStart(2, '0')}:00`;
  }

  // Filtrar horas con actividad para el gráfico
  getActiveHours(): HourData[] {
    return this.hourlyData.filter(h => h.hour >= 6 && h.hour <= 20);
  }
}
