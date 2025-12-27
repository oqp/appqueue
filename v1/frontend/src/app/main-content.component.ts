import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MenuService } from './menu.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import {RouterOutlet} from '@angular/router';

@Component({
  selector: 'app-main-content',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, RouterOutlet],
  template: `
    <main class="main-content" [class.sidebar-collapsed]="isCollapsed">
      <router-outlet></router-outlet>
<!--      <div class="content-area">

        &lt;!&ndash; Welcome Section &ndash;&gt;
        <div class="welcome-section" *ngIf="activeMenuItem === 'home'">
          <div class="welcome-card">
            <div class="welcome-header">
              <mat-icon class="welcome-icon">dashboard</mat-icon>
              <h1>Bienvenido al Sistema de Salud</h1>
            </div>
            <p class="welcome-subtitle">Gestiona eficientemente tu centro médico con nuestro sistema integral</p>

            <div class="stats-grid">
              <div class="stat-card">
                <mat-icon>people</mat-icon>
                <div class="stat-content">
                  <span class="stat-number">2,543</span>
                  <span class="stat-label">Pacientes</span>
                </div>
              </div>

              <div class="stat-card">
                <mat-icon>confirmation_number</mat-icon>
                <div class="stat-content">
                  <span class="stat-number">127</span>
                  <span class="stat-label">Tickets Activos</span>
                </div>
              </div>

              <div class="stat-card">
                <mat-icon>queue</mat-icon>
                <div class="stat-content">
                  <span class="stat-number">15</span>
                  <span class="stat-label">En Cola</span>
                </div>
              </div>

              <div class="stat-card">
                <mat-icon>desktop_windows</mat-icon>
                <div class="stat-content">
                  <span class="stat-number">8</span>
                  <span class="stat-label">Estaciones</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        &lt;!&ndash; Dynamic Content Based on Active Menu Item &ndash;&gt;
        <div class="content-section" *ngIf="activeMenuItem !== 'home'">
          <div class="section-header">
            <mat-icon>{{ getCurrentIcon() }}</mat-icon>
            <h2>{{ getCurrentTitle() }}</h2>
          </div>

          <div class="content-card">
            <p>Contenido de {{ getCurrentTitle() }}. Este es un placeholder para el módulo correspondiente.</p>
            <p class="content-description">
              Aquí se cargarían los componentes específicos para la funcionalidad de {{ getCurrentTitle() }}.
              Por ahora muestra este contenido de ejemplo.
            </p>
          </div>
        </div>

      </div>-->
    </main>
  `,
  styles: [`
    .main-content {
      margin-left: 320px;
      margin-top: 70px;
      min-height: calc(100vh - 70px);
      padding: 24px;
      transition: margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);

      &.sidebar-collapsed {
        margin-left: 125px;
      }
    }

    .content-area {
      max-width: 1400px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }

    .welcome-section {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: calc(100vh - 140px);
    }

    .welcome-card {
      background: linear-gradient(
        135deg,
        rgba(68, 119, 255, 0.12) 0%,
        rgba(59, 103, 231, 0.08) 100%
      );
      backdrop-filter: blur(25px) saturate(120%);
      -webkit-backdrop-filter: blur(25px) saturate(120%);

      border: 1px solid rgba(68, 119, 255, 0.18);
      border-radius: 32px;

      box-shadow:
        0 25px 50px rgba(68, 119, 255, 0.12),
        0 10px 30px rgba(59, 103, 231, 0.08),
        inset 0 2px 2px rgba(255, 255, 255, 0.4),
        inset 0 -1px 1px rgba(68, 119, 255, 0.05);

      padding: 48px;
      text-align: center;
      max-width: 800px;
      width: 100%;
      position: relative;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
          180deg,
          rgba(255, 255, 255, 0.15) 0%,
          transparent 50%,
          rgba(68, 119, 255, 0.03) 100%
        );
        border-radius: 32px;
        pointer-events: none;
      }
    }

    .welcome-header {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      margin-bottom: 16px;
      position: relative;
      z-index: 1;

      .welcome-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: rgba(68, 119, 255, 0.8);
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
      }

      h1 {
        font-size: 36px;
        font-weight: 700;
        color: rgba(68, 119, 255, 0.9);
        text-shadow: 0 2px 4px rgba(255, 255, 255, 0.3);
        margin: 0;
        letter-spacing: -0.025em;
      }
    }

    .welcome-subtitle {
      font-size: 18px;
      color: rgba(68, 119, 255, 0.7);
      margin-bottom: 48px;
      line-height: 1.5;
      position: relative;
      z-index: 1;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 24px;
      position: relative;
      z-index: 1;
    }

    .stat-card {
      background: rgba(255, 255, 255, 0.35);
      backdrop-filter: blur(15px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 20px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        background: rgba(255, 255, 255, 0.45);
        transform: translateY(-4px);
        box-shadow:
          0 12px 30px rgba(68, 119, 255, 0.15),
          0 4px 12px rgba(0, 0, 0, 0.05);
      }

      mat-icon {
        font-size: 36px;
        width: 36px;
        height: 36px;
        color: rgba(68, 119, 255, 0.8);
      }

      .stat-content {
        text-align: center;

        .stat-number {
          display: block;
          font-size: 28px;
          font-weight: 700;
          color: rgba(68, 119, 255, 0.9);
          line-height: 1;
        }

        .stat-label {
          font-size: 14px;
          color: rgba(68, 119, 255, 0.7);
          font-weight: 500;
        }
      }
    }

    .content-section {
      padding: 24px 0;
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 32px;

      mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: rgba(68, 119, 255, 0.8);
      }

      h2 {
        font-size: 28px;
        font-weight: 600;
        color: rgba(68, 119, 255, 0.9);
        margin: 0;
      }
    }

    .content-card {
      background: linear-gradient(
        135deg,
        rgba(68, 119, 255, 0.08) 0%,
        rgba(59, 103, 231, 0.05) 100%
      );
      backdrop-filter: blur(20px) saturate(110%);
      -webkit-backdrop-filter: blur(20px) saturate(110%);

      border: 1px solid rgba(68, 119, 255, 0.15);
      border-radius: 24px;

      box-shadow:
        0 15px 35px rgba(68, 119, 255, 0.08),
        0 5px 15px rgba(59, 103, 231, 0.05),
        inset 0 1px 1px rgba(255, 255, 255, 0.3);

      padding: 32px;
      position: relative;

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
          180deg,
          rgba(255, 255, 255, 0.1) 0%,
          transparent 50%,
          rgba(68, 119, 255, 0.02) 100%
        );
        border-radius: 24px;
        pointer-events: none;
      }

      p {
        color: rgba(68, 119, 255, 0.8);
        line-height: 1.6;
        margin-bottom: 16px;
        position: relative;
        z-index: 1;

        &:last-child {
          margin-bottom: 0;
        }
      }

      .content-description {
        color: rgba(68, 119, 255, 0.6);
        font-size: 14px;
      }
    }

    @media (max-width: 768px) {
      .main-content {
        margin-left: 0;
        padding: 16px;

        &.sidebar-collapsed {
          margin-left: 0;
        }
      }

      .welcome-card {
        padding: 32px 24px;

        .welcome-header {
          flex-direction: column;
          gap: 12px;

          .welcome-icon {
            font-size: 40px;
            width: 40px;
            height: 40px;
          }

          h1 {
            font-size: 28px;
            text-align: center;
          }
        }

        .welcome-subtitle {
          font-size: 16px;
          margin-bottom: 32px;
        }
      }

      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
      }

      .stat-card {
        padding: 20px 16px;

        mat-icon {
          font-size: 28px;
          width: 28px;
          height: 28px;
        }

        .stat-content .stat-number {
          font-size: 24px;
        }
      }

      .section-header {
        h2 {
          font-size: 24px;
        }
      }

      .content-card {
        padding: 24px 20px;
      }
    }

    @media (max-width: 480px) {
      .stats-grid {
        grid-template-columns: 1fr;
      }

      .welcome-header h1 {
        font-size: 24px;
        text-align: center;
      }
    }
  `]
})
export class MainContentComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  public isCollapsed = false;
  public activeMenuItem = 'home';

  constructor(private menuService: MenuService) {}

  ngOnInit(): void {
    this.menuService.isCollapsed$
      .pipe(takeUntil(this.destroy$))
      .subscribe(collapsed => {
        this.isCollapsed = collapsed;
      });

    this.menuService.activeMenuItem$
      .pipe(takeUntil(this.destroy$))
      .subscribe(activeItem => {
        this.activeMenuItem = activeItem;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public getCurrentTitle(): string {
    const currentItem = this.menuService.menuItems.find(
      item => item.id === this.activeMenuItem
    );
    return currentItem?.label || 'Contenido';
  }

  public getCurrentIcon(): string {
    const currentItem = this.menuService.menuItems.find(
      item => item.id === this.activeMenuItem
    );
    return currentItem?.icon || 'dashboard';
  }
}
