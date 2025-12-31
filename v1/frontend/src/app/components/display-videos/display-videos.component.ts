import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { Subject, takeUntil } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environments';
import { AuthService } from '../../services/auth.service';

interface DisplayVideo {
  Id: number;
  VideoId: string;
  Title: string | null;
  Description: string | null;
  DisplayOrder: number;
  IsActive: boolean;
  CreatedAt?: string;
  UpdatedAt?: string;
}

@Component({
  selector: 'app-display-videos',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule
  ],
  templateUrl: './display-videos.component.html',
  styleUrls: ['./display-videos.component.scss']
})
export class DisplayVideosComponent implements OnInit, OnDestroy {
  dataSource = new MatTableDataSource<DisplayVideo>([]);
  displayedColumns: string[] = ['DisplayOrder', 'VideoId', 'Title', 'Preview', 'IsActive', 'Actions'];

  loading = false;
  totalVideos = 0;
  activeVideos = 0;

  // Form fields for new video
  newVideoId = '';
  newTitle = '';
  editingVideo: DisplayVideo | null = null;

  private destroy$ = new Subject<void>();
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadVideos();
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

  loadVideos(): void {
    this.loading = true;

    this.http.get<{videos: DisplayVideo[], total: number, active_count: number}>(`${this.apiUrl}/display/videos`, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (response) => {
        this.dataSource.data = response.videos;
        this.totalVideos = response.total;
        this.activeVideos = response.active_count;
        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.showError('Error al cargar los videos');
        console.error('Error loading videos:', error);
      }
    });
  }

  addVideo(): void {
    if (!this.newVideoId.trim()) {
      this.showError('Ingrese el ID del video de YouTube');
      return;
    }

    const videoData = {
      VideoId: this.newVideoId.trim(),
      Title: this.newTitle.trim() || null,
      DisplayOrder: this.totalVideos
    };

    this.loading = true;

    this.http.post<DisplayVideo>(`${this.apiUrl}/display/videos`, videoData, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.showSuccess('Video agregado correctamente');
        this.newVideoId = '';
        this.newTitle = '';
        this.loadVideos();
      },
      error: (error) => {
        this.loading = false;
        this.showError(error.error?.detail || 'Error al agregar el video');
      }
    });
  }

  toggleActive(video: DisplayVideo): void {
    this.http.post<DisplayVideo>(`${this.apiUrl}/display/videos/${video.Id}/toggle-active`, {}, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: (updatedVideo) => {
        const status = updatedVideo.IsActive ? 'activado' : 'desactivado';
        this.showSuccess(`Video ${status}`);
        this.loadVideos();
      },
      error: (error) => {
        this.showError('Error al cambiar estado del video');
        console.error('Error toggling video:', error);
      }
    });
  }

  updateOrder(video: DisplayVideo, newOrder: number): void {
    if (newOrder < 0) return;

    this.http.patch<DisplayVideo>(`${this.apiUrl}/display/videos/${video.Id}/order`, { new_order: newOrder }, {
      headers: this.getAuthHeaders()
    }).subscribe({
      next: () => {
        this.loadVideos();
      },
      error: (error) => {
        this.showError('Error al actualizar orden');
        console.error('Error updating order:', error);
      }
    });
  }

  deleteVideo(video: DisplayVideo): void {
    if (confirm(`¿Está seguro de eliminar el video "${video.Title || video.VideoId}"?`)) {
      this.http.delete(`${this.apiUrl}/display/videos/${video.Id}`, {
        headers: this.getAuthHeaders()
      }).subscribe({
        next: () => {
          this.showSuccess('Video eliminado correctamente');
          this.loadVideos();
        },
        error: (error) => {
          this.showError('Error al eliminar el video');
          console.error('Error deleting video:', error);
        }
      });
    }
  }

  moveUp(video: DisplayVideo): void {
    if (video.DisplayOrder > 0) {
      this.updateOrder(video, video.DisplayOrder - 1);
    }
  }

  moveDown(video: DisplayVideo): void {
    this.updateOrder(video, video.DisplayOrder + 1);
  }

  getYoutubeThumbnail(videoId: string): string {
    return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
  }

  getYoutubeUrl(videoId: string): string {
    return `https://www.youtube.com/watch?v=${videoId}`;
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
