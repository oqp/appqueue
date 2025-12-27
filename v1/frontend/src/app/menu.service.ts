import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import {Router} from '@angular/router';

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  route?: string;
}

@Injectable({
  providedIn: 'root'
})
export class MenuService {
  private isCollapsedSubject = new BehaviorSubject<boolean>(false);
  private activeMenuItemSubject = new BehaviorSubject<string>('home');

  public isCollapsed$: Observable<boolean> = this.isCollapsedSubject.asObservable();
  public activeMenuItem$: Observable<string> = this.activeMenuItemSubject.asObservable();

  public menuItems: MenuItem[] = [
    { id: 'home', label: 'Inicio', icon: 'home', route: '/home' },
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
    { id: 'patients', label: 'Gestión de Pacientes', icon: 'people', route: '/patients' },
    { id: 'tickets', label: 'Tickets', icon: 'confirmation_number', route: '/tickets' },
    { id: 'queues', label: 'Colas', icon: 'queue', route: '/queues' },
    { id: 'workstations', label: 'Estaciones de Trabajo', icon: 'desktop_windows', route: '/workstations' },
    { id: 'servicetypes', label: 'Tipos de Atenciones', icon: 'category', route: '/servicetypes' },
    { id: 'users', label: 'Usuarios', icon: 'group', route: '/users' },
    { id: 'reports', label: 'Reportes', icon: 'assessment', route: '/reports' },
    { id: 'notifications', label: 'Notificaciones', icon: 'notifications', route: '/notifications' },
    { id: 'websocket', label: 'Websocket', icon: 'wifi', route: '/websocket' }
  ];

  constructor(private router: Router) {
    this.checkScreenSize();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', () => this.checkScreenSize());
    }
  }

  public toggleCollapse(): void {
    this.isCollapsedSubject.next(!this.isCollapsedSubject.value);
  }

  public setCollapsed(collapsed: boolean): void {
    this.isCollapsedSubject.next(collapsed);
  }

  public setActiveMenuItem(itemId: string): void {
    this.activeMenuItemSubject.next(itemId);

    // Navegar a la ruta correspondiente
    const menuItem = this.menuItems.find(item => item.id === itemId);
    if (menuItem?.route) {
      this.router.navigate([menuItem.route]);
    }
  }

  public getActiveMenuItem(): string {
    return this.activeMenuItemSubject.value;
  }

  public isMenuCollapsed(): boolean {
    return this.isCollapsedSubject.value;
  }

  private checkScreenSize(): void {
    if (typeof window !== 'undefined') {
      const isMobile = window.innerWidth <= 768;
      if (isMobile && !this.isCollapsedSubject.value) {
        this.setCollapsed(true);
      }
    }
  }
}
