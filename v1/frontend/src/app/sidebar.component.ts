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
      width: 280px;
      z-index: 900;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);

      &.collapsed {
        width: 85px;

        .menu-container {
          width: 85px;
          padding: 16px 8px;
        }

        .menu-item {
          width: 54px !important;
          height: 54px !important;
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
      width: 280px;
      overflow-y: auto;
      overflow-x: hidden;

      background: linear-gradient(
        135deg,
        rgba(68, 119, 255, 0.15) 0%,
        rgba(59, 103, 231, 0.12) 100%
      );
      backdrop-filter: blur(20px) saturate(120%);
      -webkit-backdrop-filter: blur(20px) saturate(120%);

      border: 1px solid rgba(68, 119, 255, 0.18);
      border-radius: 28px;

      box-shadow:
        0 20px 40px rgba(68, 119, 255, 0.12),
        0 8px 24px rgba(59, 103, 231, 0.08),
        inset 0 2px 2px rgba(255, 255, 255, 0.4),
        inset 0 -1px 1px rgba(68, 119, 255, 0.05);

      padding: 20px 16px;
      align-items: flex-start;
      gap: 12px;
      position: relative;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);

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
        border-radius: 28px;
        pointer-events: none;
      }

      &::-webkit-scrollbar {
        width: 6px;
      }

      &::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(68, 119, 255, 0.3);
        border-radius: 3px;

        &:hover {
          background: rgba(68, 119, 255, 0.5);
        }
      }
    }

    .menu-item {
      display: flex !important;
      justify-content: flex-start;
      align-items: center;
      width: 100% !important;
      height: 54px !important;
      cursor: pointer;
      border: none;
      border-radius: 18px;
      position: relative;
      z-index: 1;
      gap: 16px;
      padding: 0 16px;

      background: rgba(255, 255, 255, 0.3);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      color: rgba(68, 119, 255, 0.7);

      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);

      mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
        line-height: 24px;
        color: inherit;
        transition: all 0.3s ease;
        flex-shrink: 0;
      }

      .menu-label {
        font-size: 14px;
        font-weight: 500;
        color: inherit;
        white-space: nowrap;
        transition: all 0.3s ease;
        opacity: 1;
        overflow: hidden;
      }

      &:hover:not(.active) {
        background: rgba(255, 255, 255, 0.5);
        border-color: rgba(68, 119, 255, 0.3);
        transform: translateX(4px);
        color: rgba(68, 119, 255, 0.9);
        box-shadow:
          0 6px 20px rgba(68, 119, 255, 0.15),
          0 2px 8px rgba(0, 0, 0, 0.05);
      }

      &.active {
        background: linear-gradient(
          135deg,
          rgba(68, 119, 255, 0.95) 0%,
          rgba(59, 103, 231, 0.95) 100%
        );
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(68, 119, 255, 0.4);
        color: white;
        transform: translateX(8px) scale(1.02);
        box-shadow:
          0 8px 24px rgba(68, 119, 255, 0.35),
          0 2px 8px rgba(59, 103, 231, 0.25),
          inset 0 1px 1px rgba(255, 255, 255, 0.3);

        mat-icon, .menu-label {
          color: white;
          filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
        }

        &::after {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 90%;
          height: 90%;
          border-radius: 16px;
          background: radial-gradient(
            circle at center,
            rgba(255, 255, 255, 0.1) 0%,
            transparent 60%
          );
          opacity: 0;
          animation: pulseGlow 2s ease-in-out infinite;
        }
      }

      &:focus-visible {
        outline: 2px solid rgba(68, 119, 255, 0.5);
        outline-offset: 2px;
      }
    }

    @keyframes pulseGlow {
      0%, 100% {
        opacity: 0;
      }
      50% {
        opacity: 0.6;
      }
    }

    .menu-container {
      animation: gentleFloat 8s ease-in-out infinite;
    }

    @keyframes gentleFloat {
      0%, 100% {
        transform: translateY(0px);
      }
      50% {
        transform: translateY(-5px);
      }
    }

    @media (max-width: 768px) {
      .sidebar {
        left: -320px;

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
