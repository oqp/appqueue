import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatRippleModule],
  template: `
    <header class="app-header">
      <div class="header-left">
        <button
          mat-icon-button
          class="menu-toggle"
          (click)="onToggleMenu()"
          matRipple
          [matRippleCentered]="true">
          <mat-icon>menu</mat-icon>
        </button>

        <div class="logo-container">
          <img src="assets/logo.png" alt="Logo" class="logo" (error)="onImageError($event)">
          <span class="app-title">QFlowXpert</span>
        </div>
      </div>

      <div class="header-right">
        <button
          mat-icon-button
          class="avatar-button"
          (click)="onToggleUserMenu()"
          matRipple
          [matRippleCentered]="true">
          <mat-icon>account_circle</mat-icon>
        </button>
      </div>
    </header>
  `,
  styles: [`
    .app-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      height: 70px;
      padding: 0 24px;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1000;

      //background: linear-gradient(
      //  135deg,
      //  rgba(68, 119, 255, 0.12) 0%,
      //  rgba(59, 103, 231, 0.08) 100%
      //);
      backdrop-filter: blur(20px) saturate(120%);
      -webkit-backdrop-filter: blur(20px) saturate(120%);
      border-bottom: 1px solid rgba(68, 119, 255, 0.15);

      box-shadow:
        0 4px 20px rgba(68, 119, 255, 0.08),
        inset 0 1px 1px rgba(255, 255, 255, 0.3);
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .menu-toggle {
      width: 48px !important;
      height: 48px !important;
      background: rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 14px;
      color: rgba(68, 119, 255, 0.8);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        background: rgba(255, 255, 255, 0.35);
        color: rgba(68, 119, 255, 1);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(68, 119, 255, 0.15);
      }

      mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
      }
    }

    .logo-container {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo {
      width: 40px;
      height: 40px;
      object-fit: contain;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
      border-radius: 8px;
    }

    .app-title {
      font-size: 20px;
      font-weight: 600;
      color: rgba(68, 119, 255, 0.9);
      text-shadow: 0 1px 2px rgba(255, 255, 255, 0.5);
      letter-spacing: -0.025em;
    }

    .header-right {
      display: flex;
      align-items: center;
    }

    .avatar-button {
      width: 48px !important;
      height: 48px !important;
      background: rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      color: rgba(68, 119, 255, 0.8);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        background: rgba(255, 255, 255, 0.35);
        color: rgba(68, 119, 255, 1);
        transform: translateY(-1px) scale(1.05);
        box-shadow: 0 4px 12px rgba(68, 119, 255, 0.15);
      }

      mat-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
      }
    }

    @media (max-width: 768px) {
      .app-header {
        padding: 0 16px;
      }

      .app-title {
        display: none;
      }

      .logo {
        width: 36px;
        height: 36px;
      }
    }
  `]
})
export class HeaderComponent {
  @Output() toggleMenu = new EventEmitter<void>();
  @Output() toggleUserMenu = new EventEmitter<void>();

  onToggleMenu(): void {
    this.toggleMenu.emit();
  }

  onToggleUserMenu(): void {
    this.toggleUserMenu.emit();
  }

  onImageError(event: any): void {
    // Fallback to a default icon if logo fails to load
    event.target.style.display = 'none';
  }
}
