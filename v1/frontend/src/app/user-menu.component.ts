import { Component, Input, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
//import { MatRippleModule } from '@angular/material/core';

export interface UserMenuOption {
  id: string;
  label: string;
  icon: string;
  action?: () => void;
}

@Component({
  selector: 'app-user-menu',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  template: `
    <div
      class="user-menu-overlay"
      [class.show]="isVisible"
      (click)="onClose()"
      [style.display]="isVisible ? 'block' : 'none'">

      <div
        class="user-menu"
        [class.show]="isVisible"
        (click)="$event.stopPropagation()">

        <div class="menu-header">
          <div class="user-avatar">
            <mat-icon>account_circle</mat-icon>
          </div>
          <div class="user-info">
            <span class="user-name">Usuario</span>
            <span class="user-status">En línea</span>
          </div>
        </div>

        <div class="menu-divider"></div>

        <div class="menu-options">
          <button
            *ngFor="let option of menuOptions; trackBy: trackByOptionId"
            class="menu-option"
            (click)="onOptionClick(option)"
            >
            <mat-icon class="option-icon">{{ option.icon }}</mat-icon>
            <span class="option-label">{{ option.label }}</span>
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .user-menu-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.2);
      backdrop-filter: blur(2px);
      z-index: 2000;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &.show {
        opacity: 1;
        visibility: visible;
      }
    }

    .user-menu {
      position: absolute;
      top: 80px;
      right: 24px;
      width: 280px;
      max-height: 400px;
      overflow-y: auto;

      background: linear-gradient(
        135deg,
        rgba(68, 119, 255, 0.18) 0%,
        rgba(59, 103, 231, 0.15) 100%
      );
      backdrop-filter: blur(25px) saturate(130%);
      -webkit-backdrop-filter: blur(25px) saturate(130%);

      border: 1px solid rgba(68, 119, 255, 0.2);
      border-radius: 24px;

      box-shadow:
        0 25px 50px rgba(68, 119, 255, 0.15),
        0 10px 30px rgba(59, 103, 231, 0.1),
        inset 0 2px 2px rgba(255, 255, 255, 0.5),
        inset 0 -1px 1px rgba(68, 119, 255, 0.08);

      transform: translateY(-20px) scale(0.9);
      opacity: 0;
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
          rgba(255, 255, 255, 0.2) 0%,
          transparent 50%,
          rgba(68, 119, 255, 0.05) 100%
        );
        border-radius: 24px;
        pointer-events: none;
      }

      &.show {
        transform: translateY(0) scale(1);
        opacity: 1;
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

    .menu-header {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px 24px 16px;
      position: relative;
      z-index: 1;
    }

    .user-avatar {
      width: 50px;
      height: 50px;
      background: linear-gradient(
        135deg,
        rgba(68, 119, 255, 0.9) 0%,
        rgba(59, 103, 231, 0.9) 100%
      );
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow:
        0 4px 12px rgba(68, 119, 255, 0.25),
        inset 0 1px 1px rgba(255, 255, 255, 0.3);

      mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: white;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2));
      }
    }

    .user-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .user-name {
      font-size: 16px;
      font-weight: 600;
      color: rgba(68, 119, 255, 0.9);
      text-shadow: 0 1px 2px rgba(255, 255, 255, 0.3);
    }

    .user-status {
      font-size: 12px;
      color: rgba(68, 119, 255, 0.6);
      display: flex;
      align-items: center;
      gap: 6px;

      &::before {
        content: '';
        width: 6px;
        height: 6px;
        background: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.3);
      }
    }

    .menu-divider {
      height: 1px;
      background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(68, 119, 255, 0.2) 50%,
        transparent 100%
      );
      margin: 0 20px 16px;
    }

    .menu-options {
      padding: 0 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      position: relative;
      z-index: 1;
    }

    .menu-option {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px 16px;
      border: none;
      background: rgba(255, 255, 255, 0.25);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.4);
      border-radius: 16px;
      color: rgba(68, 119, 255, 0.8);
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      text-align: left;
      width: 100%;

      .option-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: inherit;
        flex-shrink: 0;
      }

      .option-label {
        font-size: 14px;
        font-weight: 500;
        color: inherit;
      }

      &:hover {
        background: rgba(255, 255, 255, 0.4);
        border-color: rgba(68, 119, 255, 0.4);
        color: rgba(68, 119, 255, 1);
        transform: translateX(4px);
        box-shadow:
          0 4px 12px rgba(68, 119, 255, 0.15),
          0 1px 4px rgba(0, 0, 0, 0.05);
      }

      &:active {
        transform: translateX(2px) scale(0.98);
      }

      &:nth-last-child(-n+2) {
        border-color: rgba(239, 68, 68, 0.3);
        color: rgba(239, 68, 68, 0.8);

        &:hover {
          background: rgba(239, 68, 68, 0.1);
          border-color: rgba(239, 68, 68, 0.5);
          color: rgba(239, 68, 68, 1);
        }
      }
    }

    @media (max-width: 768px) {
      .user-menu {
        right: 16px;
        width: calc(100vw - 32px);
        max-width: 320px;
      }
    }
  `]
})
export class UserMenuComponent {
  @Input() isVisible = false;
  @Output() close = new EventEmitter<void>();
  @Output() optionSelected = new EventEmitter<string>();

  public menuOptions: UserMenuOption[] = [
    { id: 'login', label: 'Iniciar Sesión', icon: 'login' },
    { id: 'user', label: 'Mi Perfil', icon: 'person' },
    { id: 'about', label: 'Acerca de', icon: 'info' },
    { id: 'logout', label: 'Cerrar Sesión', icon: 'logout' },
    { id: 'exit', label: 'Salir', icon: 'exit_to_app' }
  ];

  @HostListener('document:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Escape' && this.isVisible) {
      this.onClose();
    }
  }

  public onClose(): void {
    this.close.emit();
  }

  public onOptionClick(option: UserMenuOption): void {
    this.optionSelected.emit(option.id);
    if (option.action) {
      option.action();
    }
    this.onClose();
  }

  public trackByOptionId(index: number, option: UserMenuOption): string {
    return option.id;
  }
}
