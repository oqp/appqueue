import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HeaderComponent } from './header.component';
import { SidebarComponent } from './sidebar.component';
import { MainContentComponent } from './main-content.component';
import { UserMenuComponent } from './user-menu.component';
import { MenuService } from './menu.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HeaderComponent,
    SidebarComponent,
    MainContentComponent,
    UserMenuComponent
  ],
  template: `
    <!-- Floating orbs (always active from your original styles) -->
    <div class="floating-orb orb-1"></div>
    <div class="floating-orb orb-2"></div>
    <div class="floating-orb orb-3"></div>

    <!-- Header -->
    <app-header
      (toggleMenu)="onToggleMenu()"
      (toggleUserMenu)="onToggleUserMenu()">
    </app-header>

    <!-- Sidebar -->
    <app-sidebar></app-sidebar>

    <!-- Main Content -->
    <app-main-content></app-main-content>

    <!-- User Menu -->
    <app-user-menu
      [isVisible]="isUserMenuVisible"
      (close)="onCloseUserMenu()"
      (optionSelected)="onUserMenuOption($event)">
    </app-user-menu>

    <!-- Mobile Overlay for Sidebar -->
    <div
      class="mobile-overlay"
      [class.show]="!isMenuCollapsed && isMobile"
      (click)="onCloseMobileMenu()"
      *ngIf="isMobile">
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      height: 100vh;
      position: relative;
    }

    .floating-orb {
      position: fixed;
      border-radius: 50%;
      pointer-events: none;
      z-index: 0;

      &.orb-1 {
        width: 300px;
        height: 300px;
        background: radial-gradient(
          circle at center,
          rgba(68, 119, 255, 0.02) 0%,
          transparent 70%
        );
        top: 15%;
        left: 10%;
        animation: floatOrb 20s ease-in-out infinite;
      }

      &.orb-2 {
        width: 250px;
        height: 250px;
        background: radial-gradient(
          circle at center,
          rgba(100, 149, 255, 0.025) 0%,
          transparent 60%
        );
        bottom: 20%;
        right: 15%;
        animation: floatOrb 25s ease-in-out infinite reverse;
      }

      &.orb-3 {
        width: 350px;
        height: 350px;
        background: radial-gradient(
          circle at center,
          rgba(150, 170, 200, 0.03) 0%,
          transparent 50%
        );
        top: 60%;
        left: 60%;
        animation: floatOrb 30s ease-in-out infinite;
      }
    }

    @keyframes floatOrb {
      0%, 100% {
        transform: translate(0px, 0px) scale(1);
      }
      33% {
        transform: translate(30px, -30px) scale(1.05);
      }
      66% {
        transform: translate(-20px, 20px) scale(0.95);
      }
    }

    .mobile-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(2px);
      z-index: 850;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;

      &.show {
        opacity: 1;
        visibility: visible;
      }
    }

    @media (max-width: 768px) {
      .floating-orb {
        &.orb-1 {
          width: 200px;
          height: 200px;
          top: 10%;
          left: 5%;
        }

        &.orb-2 {
          width: 180px;
          height: 180px;
          bottom: 15%;
          right: 5%;
        }

        &.orb-3 {
          width: 220px;
          height: 220px;
          top: 50%;
          left: 50%;
        }
      }
    }
  `]
})
export class AppComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  public isUserMenuVisible = false;
  public isMenuCollapsed = false;
  public isMobile = false;
  public title = 'HealthSystem';

  constructor(private menuService: MenuService) {
    this.checkScreenSize();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', () => this.checkScreenSize());
    }
  }

  ngOnInit(): void {
    this.menuService.isCollapsed$
      .pipe(takeUntil(this.destroy$))
      .subscribe(collapsed => {
        this.isMenuCollapsed = collapsed;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', () => this.checkScreenSize());
    }
  }

  public onToggleMenu(): void {
    this.menuService.toggleCollapse();
  }

  public onToggleUserMenu(): void {
    this.isUserMenuVisible = !this.isUserMenuVisible;
  }

  public onCloseUserMenu(): void {
    this.isUserMenuVisible = false;
  }

  public onUserMenuOption(optionId: string): void {
    console.log('User menu option selected:', optionId);

    switch (optionId) {
      case 'login':
        this.handleLogin();
        break;
      case 'logout':
        this.handleLogout();
        break;
      case 'user':
        this.handleUserProfile();
        break;
      case 'exit':
        this.handleExit();
        break;
      case 'about':
        this.handleAbout();
        break;
      default:
        console.log('Unknown option:', optionId);
    }
  }

  public onCloseMobileMenu(): void {
    if (this.isMobile) {
      this.menuService.setCollapsed(true);
    }
  }

  private checkScreenSize(): void {
    if (typeof window !== 'undefined') {
      this.isMobile = window.innerWidth <= 768;
    }
  }

  private handleLogin(): void {
    console.log('Login action triggered');
    // TODO: Implement login logic
  }

  private handleLogout(): void {
    console.log('Logout action triggered');
    // TODO: Implement logout logic
  }

  private handleUserProfile(): void {
    console.log('User profile action triggered');
    // TODO: Navigate to user profile
  }

  private handleExit(): void {
    console.log('Exit action triggered');
    // TODO: Implement exit logic
  }

  private handleAbout(): void {
    console.log('About action triggered');
    // TODO: Show about dialog
  }
}
