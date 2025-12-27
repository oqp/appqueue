// login.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';

// Services
import { AuthService } from '../../services/auth.service';

// Interfaces
interface LoginForm {
  username: string;
  password: string;
  rememberMe: boolean;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    MatDialogModule
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit, OnDestroy {
  // Form
  loginForm: FormGroup;

  // State
  loading = false;
  hidePassword = true;
  returnUrl: string = '/dashboard';

  // Error handling
  errorMessage: string = '';
  loginAttempts = 0;
  maxAttempts = 5;
  isBlocked = false;
  blockTimeRemaining = 0;

  // Demo users info
  showDemoInfo = true;
  demoUsers = [
    { username: 'admin', password: 'admin123', role: 'Administrador' },
    { username: 'supervisor', password: 'sup123', role: 'Supervisor' },
    { username: 'tecnico', password: 'tec123', role: 'Técnico' },
    { username: 'recepcion', password: 'rec123', role: 'Recepcionista' }
  ];

  // Clock for UI
  currentTime = new Date();
  private clockInterval: any;

  // Cleanup
  private destroy$ = new Subject<void>();

  // Animation state
  cardAnimationClass = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    // Initialize form with validation
    this.loginForm = this.fb.group({
      username: ['', [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(50)
      ]],
      password: ['', [
        Validators.required,
        Validators.minLength(4),
        Validators.maxLength(100)
      ]],
      rememberMe: [false]
    });
  }

  ngOnInit(): void {
    // Check if user is already logged in
    this.authService.isAuthenticated$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(isAuthenticated => {
      if (isAuthenticated) {
        this.router.navigate([this.returnUrl]);
      }
    });

    // Get return URL from route parameters or default to dashboard
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] ||
      localStorage.getItem('redirectUrl') ||
      '/dashboard';

    // Start clock
    this.startClock();

    // Add entrance animation
    setTimeout(() => {
      this.cardAnimationClass = 'card-entrance';
    }, 100);

    // Check for blocked status
    this.checkBlockedStatus();

    // Focus on username field
    setTimeout(() => {
      const usernameInput = document.getElementById('username-input');
      if (usernameInput) {
        usernameInput.focus();
      }
    }, 500);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    if (this.clockInterval) {
      clearInterval(this.clockInterval);
    }
  }

  // ========== FORM METHODS ==========

  /**
   * Handle login form submission
   */
  onSubmit(): void {
    // Reset error message
    this.errorMessage = '';

    // Check if form is valid
    if (this.loginForm.invalid) {
      this.markFormGroupTouched(this.loginForm);
      this.shakeCard();
      return;
    }

    // Check if blocked
    if (this.isBlocked) {
      this.showError(`Cuenta bloqueada. Espere ${this.blockTimeRemaining} segundos.`);
      this.shakeCard();
      return;
    }

    // Get form values
    const { username, password, rememberMe } = this.loginForm.value;

    // Start loading
    this.loading = true;

    // Call auth service
    this.authService.login(username, password, rememberMe).subscribe({
      next: (response) => {
        this.loading = false;

        // Show success message
        this.showSuccess(`¡Bienvenido ${response.user.full_name}!`);

        // Clear redirect URL from localStorage
        localStorage.removeItem('redirectUrl');

        // Navigate to return URL
        setTimeout(() => {
          this.router.navigate([this.returnUrl]);
        }, 500);
      },
      error: (error) => {
        this.loading = false;
        this.loginAttempts++;

        // Handle specific error cases
        if (error.message.includes('Credenciales inválidas')) {
          this.errorMessage = 'Usuario o contraseña incorrectos';

          // Check if should block
          if (this.loginAttempts >= this.maxAttempts) {
            this.blockAccount();
          } else {
            const remaining = this.maxAttempts - this.loginAttempts;
            this.errorMessage += `. ${remaining} intentos restantes.`;
          }
        } else if (error.message.includes('Usuario inactivo')) {
          this.errorMessage = 'Su cuenta está desactivada. Contacte al administrador.';
        } else if (error.message.includes('sesión expirada')) {
          this.errorMessage = 'Su sesión ha expirado. Por favor, ingrese nuevamente.';
        } else {
          this.errorMessage = error.message || 'Error al iniciar sesión. Intente nuevamente.';
        }

        // Visual feedback
        this.shakeCard();
        this.showError(this.errorMessage);

        // Clear password field
        this.loginForm.patchValue({ password: '' });
      }
    });
  }

  /**
   * Handle forgot password
   */
  onForgotPassword(): void {
    const username = this.loginForm.get('username')?.value;

    if (username) {
      // TODO: Open forgot password dialog with username pre-filled
      this.showInfo('Funcionalidad de recuperación de contraseña próximamente');
    } else {
      this.showInfo('Ingrese su nombre de usuario primero');
      const usernameInput = document.getElementById('username-input');
      if (usernameInput) {
        usernameInput.focus();
      }
    }
  }

  /**
   * Fill demo credentials
   */
  fillDemoCredentials(username: string, password: string): void {
    this.loginForm.patchValue({
      username: username,
      password: password,
      rememberMe: false
    });

    // Auto submit after a short delay
    setTimeout(() => {
      this.onSubmit();
    }, 300);
  }

  /**
   * Handle Enter key press
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !this.loading) {
      this.onSubmit();
    }
  }

  // ========== UTILITY METHODS ==========

  /**
   * Mark all form fields as touched to show validation errors
   */
  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }

  /**
   * Block account after too many attempts
   */
  private blockAccount(): void {
    this.isBlocked = true;
    this.blockTimeRemaining = 300; // 5 minutes

    const interval = setInterval(() => {
      this.blockTimeRemaining--;

      if (this.blockTimeRemaining <= 0) {
        this.isBlocked = false;
        this.loginAttempts = 0;
        clearInterval(interval);
        this.showInfo('Puede intentar iniciar sesión nuevamente');
      }
    }, 1000);
  }

  /**
   * Check if account is blocked in localStorage
   */
  private checkBlockedStatus(): void {
    const blockedUntil = localStorage.getItem('login_blocked_until');

    if (blockedUntil) {
      const blockedTime = new Date(blockedUntil);
      const now = new Date();

      if (blockedTime > now) {
        this.isBlocked = true;
        this.blockTimeRemaining = Math.floor((blockedTime.getTime() - now.getTime()) / 1000);
        this.blockAccount(); // Resume countdown
      } else {
        localStorage.removeItem('login_blocked_until');
      }
    }
  }

  /**
   * Start clock for UI
   */
  private startClock(): void {
    this.clockInterval = setInterval(() => {
      this.currentTime = new Date();
    }, 1000);
  }

  /**
   * Shake card animation for errors
   */
  private shakeCard(): void {
    this.cardAnimationClass = 'card-shake';
    setTimeout(() => {
      this.cardAnimationClass = 'card-entrance';
    }, 500);
  }

  // ========== VALIDATORS ==========

  /**
   * Get error message for form field
   */
  getErrorMessage(fieldName: string): string {
    const control = this.loginForm.get(fieldName);

    if (!control || !control.errors || !control.touched) {
      return '';
    }

    if (control.errors['required']) {
      return fieldName === 'username' ?
        'El usuario es requerido' :
        'La contraseña es requerida';
    }

    if (control.errors['minlength']) {
      const minLength = control.errors['minlength'].requiredLength;
      return `Mínimo ${minLength} caracteres`;
    }

    if (control.errors['maxlength']) {
      const maxLength = control.errors['maxlength'].requiredLength;
      return `Máximo ${maxLength} caracteres`;
    }

    return 'Campo inválido';
  }

  // ========== NOTIFICATIONS ==========

  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 3000,
      panelClass: ['success-snackbar'],
      horizontalPosition: 'end',
      verticalPosition: 'top'
    });
  }

  private showError(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 5000,
      panelClass: ['error-snackbar'],
      horizontalPosition: 'end',
      verticalPosition: 'top'
    });
  }

  private showInfo(message: string): void {
    this.snackBar.open(message, 'OK', {
      duration: 3000,
      panelClass: ['info-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom'
    });
  }
}
