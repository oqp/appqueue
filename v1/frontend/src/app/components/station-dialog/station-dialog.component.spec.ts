import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StationDialogComponent } from './station-dialog.component';

describe('StationDialogComponent', () => {
  let component: StationDialogComponent;
  let fixture: ComponentFixture<StationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StationDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
