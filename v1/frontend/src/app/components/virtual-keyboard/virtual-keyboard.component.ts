import { Component, EventEmitter, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-virtual-keyboard',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  template: `
    <div class="virtual-keyboard">
      <div class="keyboard-display">
        <div class="display-value">{{ displayValue || 'Ingrese número' }}</div>
      </div>

      <div class="keyboard-grid">
        <button mat-raised-button
                *ngFor="let num of numbers"
                (click)="addNumber(num)"
                class="key-button number-key">
          {{ num }}
        </button>

        <button mat-raised-button
                (click)="clear()"
                class="key-button clear-key">
          <mat-icon>clear</mat-icon>
          Borrar
        </button>

        <button mat-raised-button
                (click)="addNumber('0')"
                class="key-button number-key zero-key">
          0
        </button>

        <button mat-raised-button
                (click)="backspace()"
                class="key-button backspace-key">
          <mat-icon>backspace</mat-icon>
        </button>
      </div>

      <button mat-raised-button
              color="primary"
              (click)="submit()"
              [disabled]="!isValid"
              class="submit-button">
        <mat-icon>search</mat-icon>
        BUSCAR PACIENTE
      </button>
    </div>
  `,
  styles: [`
    .virtual-keyboard {
      width: 100%;
      max-width: 400px;
      margin: 0 auto;
    }

    .keyboard-display {
      background: white;
      border: 3px solid #e0e0e0;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      min-height: 80px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .display-value {
      font-size: 36px;
      font-weight: 500;
      color: #333;
      letter-spacing: 4px;
      text-align: center;
      font-family: 'Courier New', monospace;
    }

    .keyboard-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 20px;
    }

    .key-button {
      height: 80px;
      font-size: 28px;
      font-weight: 500;
      border-radius: 12px;
      background: white;
      color: #333;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      transition: all 0.2s;
    }

    .key-button:active {
      transform: scale(0.95);
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .number-key {
      font-size: 32px;
    }

    .clear-key {
      background: #ff6b6b;
      color: white;
      font-size: 18px;
    }

    .backspace-key {
      background: #ffd93d;
      color: #333;
    }

    .zero-key {
      grid-column: 2;
    }

    .submit-button {
      width: 100%;
      height: 80px;
      font-size: 24px;
      font-weight: 500;
      border-radius: 16px;
    }

    .submit-button mat-icon {
      margin-right: 10px;
      font-size: 28px;
    }

    /* Para pantallas táctiles grandes */
    @media (min-height: 1900px) {
      .keyboard-display {
        min-height: 100px;
      }

      .display-value {
        font-size: 48px;
      }

      .key-button {
        height: 100px;
        font-size: 36px;
      }

      .number-key {
        font-size: 42px;
      }

      .submit-button {
        height: 100px;
        font-size: 32px;
      }
    }
  `]
})
export class VirtualKeyboardComponent {
  @Input() minLength: number = 8;
  @Input() maxLength: number = 20;
  @Output() onSubmit = new EventEmitter<string>();
  @Output() onValueChange = new EventEmitter<string>();

  displayValue: string = '';
  numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

  get isValid(): boolean {
    return this.displayValue.length >= this.minLength &&
      this.displayValue.length <= this.maxLength;
  }

  addNumber(num: string): void {
    if (this.displayValue.length < this.maxLength) {
      this.displayValue += num;
      this.onValueChange.emit(this.displayValue);
    }
  }

  backspace(): void {
    if (this.displayValue.length > 0) {
      this.displayValue = this.displayValue.slice(0, -1);
      this.onValueChange.emit(this.displayValue);
    }
  }

  clear(): void {
    this.displayValue = '';
    this.onValueChange.emit(this.displayValue);
  }

  submit(): void {
    if (this.isValid) {
      this.onSubmit.emit(this.displayValue);
    }
  }
}
