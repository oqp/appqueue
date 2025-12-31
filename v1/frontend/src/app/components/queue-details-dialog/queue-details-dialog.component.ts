// queue-details-dialog.component.ts
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { QueueService } from '../../services/queue.service';

interface QueueDetails {
  queue: any;
  tickets?: any[];
  statistics?: any;
}

@Component({
  selector: 'app-queue-details-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatListModule,
    MatChipsModule,
    MatTabsModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatCardModule
  ],
  template: `
    <h2 mat-dialog-title>
      <div class="title-content">
        <mat-icon [style.color]="data.queue.Color || '#4477ff'">queue</mat-icon>
        <span>{{data.queue.ServiceName}}</span>
        <span class="subtitle">{{data.queue.ServiceCode}}</span>
      </div>
    </h2>

    <mat-dialog-content>
      <mat-tab-group>
        <!-- Tab 1: Información General -->
        <mat-tab label="Información General">
          <ng-container *matTabContent>
            <div class="tab-container">
              <!-- Estado Actual -->
              <div class="info-section">
                <h4>Estado Actual</h4>
                <div class="info-grid">
                  <div class="info-card">
                    <mat-icon>people</mat-icon>
                    <div class="info-text">
                      <span class="value">{{data.queue.QueueLength}}</span>
                      <span class="label">Personas en Espera</span>
                    </div>
                  </div>
                  <div class="info-card">
                    <mat-icon>schedule</mat-icon>
                    <div class="info-text">
                      <span class="value">{{data.queue.AverageWaitTime}} min</span>
                      <span class="label">Tiempo Promedio</span>
                    </div>
                  </div>
                  <div class="info-card">
                    <mat-icon>confirmation_number</mat-icon>
                    <div class="info-text">
                      <span class="value">{{data.queue.CurrentTicketNumber || 'Ninguno'}}</span>
                      <span class="label">Ticket Actual</span>
                    </div>
                  </div>
                  <div class="info-card">
                    <mat-icon>skip_next</mat-icon>
                    <div class="info-text">
                      <span class="value">{{data.queue.NextTicketNumber || 'Ninguno'}}</span>
                      <span class="label">Siguiente Ticket</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Configuración -->
              <div class="info-section">
                <h4>Configuración</h4>
                <table class="config-table">
                  <tr>
                    <td>Tipo de Cola:</td>
                    <td><strong>{{data.queue.StationName || 'Cola General'}}</strong></td>
                  </tr>
                  <tr>
                    <td>Prefijo de Ticket:</td>
                    <td><strong>{{data.queue.TicketPrefix || 'N/A'}}</strong></td>
                  </tr>
                  <tr>
                    <td>Estado:</td>
                    <td>
                      <mat-chip [style.background-color]="getStatusColor()">
                        {{data.queue.IsActive ? 'Activa' : 'Inactiva'}}
                      </mat-chip>
                    </td>
                  </tr>
                  <tr>
                    <td>Última Actualización:</td>
                    <td><strong>{{formatDate(data.queue.LastUpdateAt)}}</strong></td>
                  </tr>
                </table>
              </div>
            </div>
          </ng-container>
        </mat-tab>

        <!-- Tab 2: Tickets -->
        <mat-tab label="Tickets (0)" [disabled]="true">
          <ng-container *matTabContent>
            <div class="tab-container">
              <div class="empty-state">
                <mat-icon>inbox</mat-icon>
                <p>No hay tickets en espera</p>
              </div>
            </div>
          </ng-container>
        </mat-tab>

        <!-- Tab 3: Estadísticas -->
        <mat-tab label="Estadísticas">
          <ng-container *matTabContent>
            <div class="tab-container">
              <div class="stats-grid">
                <div class="stat-card">
                  <mat-icon>today</mat-icon>
                  <span class="stat-value">{{data.statistics?.ticketsToday || 0}}</span>
                  <span class="stat-label">Tickets Hoy</span>
                </div>
                <div class="stat-card">
                  <mat-icon>done_all</mat-icon>
                  <span class="stat-value">{{data.statistics?.completedToday || 0}}</span>
                  <span class="stat-label">Completados</span>
                </div>
                <div class="stat-card">
                  <mat-icon>timer</mat-icon>
                  <span class="stat-value">{{data.statistics?.avgServiceTime || 0}} min</span>
                  <span class="stat-label">Tiempo Promedio</span>
                </div>
                <div class="stat-card">
                  <mat-icon>trending_up</mat-icon>
                  <span class="stat-value">{{calculateAttentionRate()}}%</span>
                  <span class="stat-label">Tasa de Atención</span>
                </div>
              </div>
            </div>
          </ng-container>
        </mat-tab>
      </mat-tab-group>
    </mat-dialog-content>

    <mat-dialog-actions>
      <button mat-button (click)="onClose()">Cerrar</button>
      <button mat-raised-button color="primary" (click)="onRefresh()">
        <mat-icon>refresh</mat-icon>
        Actualizar
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
    }

    .title-content {
      display: flex;
      align-items: center;
      gap: 8px;

      mat-icon {
        font-size: 20px;
      }

      .subtitle {
        margin-left: auto;
        font-size: 14px;
        color: #666;
      }
    }

    mat-dialog-content {
      padding: 0;
      margin: 0;
      overflow: hidden;
      display: block;
      height: 400px;
    }

    mat-tab-group {
      height: 100%;
    }

    .tab-container {
      padding: 16px;
      height: 350px;
      overflow-y: auto;
      overflow-x: hidden;
    }

    .info-section {
      margin-bottom: 20px;

      h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 500;
        color: #666;
      }
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .info-card {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      background: #f5f5f5;
      border-radius: 4px;

      mat-icon {
        color: #666;
        font-size: 20px;
      }

      .info-text {
        .value {
          display: block;
          font-size: 14px;
          font-weight: 600;
          color: #333;
        }

        .label {
          display: block;
          font-size: 11px;
          color: #666;
        }
      }
    }

    .config-table {
      width: 100%;
      font-size: 13px;

      tr {
        height: 32px;

        td {
          padding: 4px 0;

          &:first-child {
            color: #666;
            width: 40%;
          }

          strong {
            color: #333;
          }

          mat-chip {
            height: 22px;
            line-height: 22px;
            font-size: 11px;
            padding: 0 8px;
            color: white;
          }
        }
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }

    .stat-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 4px;
      text-align: center;

      mat-icon {
        font-size: 28px;
        color: #4477ff;
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 20px;
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
      }

      .stat-label {
        font-size: 11px;
        color: #666;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      color: #999;

      mat-icon {
        font-size: 48px;
        margin-bottom: 12px;
      }

      p {
        margin: 0;
        font-size: 14px;
      }
    }

    mat-dialog-actions {
      padding: 12px 16px;
      margin: 0;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
      gap: 8px;

      button mat-icon {
        font-size: 18px;
        margin-right: 4px;
      }
    }
  `]
})
export class QueueDetailsDialogComponent implements OnInit {
  loadingTickets = false;
  ticketColumns: string[] = ['position', 'ticketNumber', 'patient', 'waitTime', 'status'];

  constructor(
    public dialogRef: MatDialogRef<QueueDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: QueueDetails,
    private queueService: QueueService
  ) {
    // Agregar clase al contenedor del diálogo
    dialogRef.addPanelClass('queue-details-dialog');
  }

  ngOnInit(): void {
    this.loadTickets();
    this.loadStatistics();
  }

  loadTickets(): void {
    this.loadingTickets = true;
    const serviceTypeId = this.data.queue.ServiceTypeId;

    if (!serviceTypeId) {
      this.loadingTickets = false;
      this.data.tickets = [];
      return;
    }

    // Cargar tickets en espera para este servicio
    this.queueService.getTicketsByService(serviceTypeId, 20).subscribe({
      next: (tickets) => {
        console.log('Tickets loaded:', tickets);
        this.data.tickets = tickets || [];
        this.loadingTickets = false;
      },
      error: (error) => {
        console.error('Error loading tickets:', error);
        this.data.tickets = [];
        this.loadingTickets = false;
      }
    });
  }

  loadStatistics(): void {
    const serviceTypeId = this.data.queue.ServiceTypeId;

    if (!serviceTypeId) {
      this.data.statistics = {
        ticketsToday: 0,
        completedToday: 0,
        avgServiceTime: 0,
        maxWaitTime: 0,
        cancelledToday: 0,
        peakHour: 'N/A'
      };
      return;
    }

    // Cargar estadísticas reales del servicio
    this.queueService.getServiceStats(serviceTypeId).subscribe({
      next: (stats) => {
        console.log('Service stats loaded:', stats);
        // El backend devuelve: total_tickets, attended_tickets, pending_tickets,
        // average_wait_time, average_service_time, completion_rate, peak_hour
        this.data.statistics = {
          ticketsToday: stats.total_tickets ?? 0,
          completedToday: stats.attended_tickets ?? 0,
          avgServiceTime: Math.round(stats.average_service_time ?? 0),
          maxWaitTime: Math.round(stats.average_wait_time ?? 0),
          cancelledToday: Math.max(0, (stats.total_tickets ?? 0) - (stats.attended_tickets ?? 0) - (stats.pending_tickets ?? 0)),
          peakHour: stats.peak_hour ?? 'N/A'
        };
      },
      error: (error) => {
        console.error('Error loading statistics:', error);
        this.data.statistics = {
          ticketsToday: 0,
          completedToday: 0,
          avgServiceTime: 0,
          maxWaitTime: 0,
          cancelledToday: 0,
          peakHour: 'N/A'
        };
      }
    });
  }

  getStatusColor(): string {
    if (!this.data.queue.IsActive) return '#f5f5f5';      // Gris muy claro
    if (this.data.queue.QueueLength === 0) return '#e8f5e9';  // Verde muy claro
    if (this.data.queue.QueueLength <= 5) return '#e3f2fd';   // Azul muy claro
    if (this.data.queue.QueueLength <= 10) return '#fff3e0';  // Naranja muy claro
    return '#ffebee';  // Rojo muy claro
  }

  getTicketStatusColor(status: string): string {
    switch(status) {
      case 'Waiting': return '#ffa726';
      case 'Called': return '#42a5f5';
      case 'InProgress': return '#66bb6a';
      case 'Completed': return '#9e9e9e';
      default: return '#90a4ae';
    }
  }

  formatDate(date: string | Date): string {
    if (!date) return 'N/A';
    const d = new Date(date);
    return d.toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  calculateWaitTime(createdAt: string | Date): string {
    if (!createdAt) return '0 min';
    const created = new Date(createdAt);
    const now = new Date();
    const diffMinutes = Math.floor((now.getTime() - created.getTime()) / 60000);

    if (diffMinutes < 60) {
      return `${diffMinutes} min`;
    }
    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;
    return `${hours}h ${minutes}m`;
  }

  calculateAttentionRate(): number {
    if (!this.data.statistics) return 0;
    const total = this.data.statistics.ticketsToday || 0;
    const completed = this.data.statistics.completedToday || 0;
    if (total === 0) return 0;
    return Math.round((completed / total) * 100);
  }

  onRefresh(): void {
    this.loadTickets();
    this.loadStatistics();
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
