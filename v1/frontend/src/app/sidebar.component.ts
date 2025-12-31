import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MenuService, MenuItem } from './menu.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatRippleModule, MatTooltipModule],
  template: `
    <aside class="sidebar" [class.collapsed]="isCollapsed">
      <div class="menu-container">
        <button
          *ngFor="let item of menuItems; trackBy: trackByItemId"
          mat-icon-button
          class="menu-item"
          [class.active]="activeMenuItem === item.id"
          (click)="setActiveItem(item.id)"
          [matTooltip]="isCollapsed ? item.label : ''"
          matTooltipPosition="right"
          [disabled]="false"
        >
          <mat-icon>{{ item.icon }}</mat-icon>
          <span class="menu-label" *ngIf="!isCollapsed">{{ item.label }}</span>
        </button>
      </div>
    </aside>
  `,
  styles: [`
    .sidebar {
      position: fixed;
      top: 70px;
      left: 24px;
      bottom: 24px;
      width: 260px;
      z-index: 900;
      transition: all 0.3s ease;

      &.collapsed {
        width: 70px;

        .menu-container {
          width: 70px;
          padding: 12px 8px;
        }

        .menu-item {
          width: 50px !important;
          height: 50px !important;
          justify-content: center;
          padding: 0;

          .menu-label {
            opacity: 0;
            width: 0;
            overflow: hidden;
          }
        }
      }
    }

    .menu-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 260px;
      overflow-y: auto;
      overflow-x: hidden;

      /* Estilo AppLab: Azul oscuro sólido */
      background: linear-gradient(
          180deg,
          #1565C0 0%,
          #0D47A1 100%
      );

      border: none;
      border-radius: 12px;

      box-shadow:
        0 4px 20px rgba(13, 71, 161, 0.3),
        0 2px 8px rgba(0, 0, 0, 0.15);

      padding: 16px 12px;
      align-items: flex-start;
      gap: 6px;
      position: relative;
      transition: all 0.3s ease;

      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 2px;

        &:hover {
          background: rgba(255, 255, 255, 0.5);
        }
      }
    }

    .menu-item {
      display: flex !important;
      justify-content: flex-start;
      align-items: center;
      width: 100% !important;
      height: 46px !important;
      cursor: pointer;
      border: none;
      border-radius: 8px;
      position: relative;
      z-index: 1;
      gap: 14px;
      padding: 0 14px;

      /* Items normales: transparente con texto blanco */
      background: transparent;
      color: rgba(255, 255, 255, 0.85);

      transition: all 0.2s ease;

      mat-icon {
        font-size: 22px;
        width: 22px;
        height: 22px;
        line-height: 22px;
        color: inherit;
        transition: all 0.2s ease;
        flex-shrink: 0;
      }

      .menu-label {
        font-size: 14px;
        font-weight: 500;
        color: inherit;
        white-space: nowrap;
        transition: all 0.2s ease;
        opacity: 1;
        overflow: hidden;
      }

      &:hover:not(.active) {
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff;
      }

      &.active {
        /* Item activo: fondo blanco con texto azul */
        background: #ffffff;
        color: #1565C0;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);

        mat-icon, .menu-label {
          color: #1565C0;
        }
      }

      &:focus-visible {
        outline: 2px solid rgba(255, 255, 255, 0.5);
        outline-offset: 2px;
      }
    }

    @media (max-width: 768px) {
      .sidebar {
        left: -280px;

        &:not(.collapsed) {
          left: 16px;
        }

        &.collapsed {
          left: 16px;
        }
      }
    }
  `]

})
export class SidebarComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  public isCollapsed = false;
  public activeMenuItem = 'home';
  public menuItems: MenuItem[] = [];

  constructor(private menuService: MenuService) {}

  ngOnInit(): void {
    this.menuItems = this.menuService.menuItems;

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

  public setActiveItem(itemId: string): void {
    this.menuService.setActiveMenuItem(itemId);
  }

  public trackByItemId(index: number, item: MenuItem): string {
    return item.id;
  }
}
