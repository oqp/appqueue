/**
 * Modelos para el manejo de Tipos de Servicios (Service Types)
 * Compatible con los schemas de FastAPI/SQLAlchemy del backend
 */

export interface ServiceType {
  Id: number;
  Code: string;
  Name: string;
  Description?: string;
  Priority: number;
  AverageTimeMinutes: number;
  TicketPrefix: string;
  Color: string;
  IsActive: boolean;
  CreatedAt: Date;
  UpdatedAt?: Date;

  // Propiedades calculadas del backend
  priority_name?: string;
  is_high_priority?: boolean;
  station_count?: number;
  active_station_count?: number;
  current_queue_count?: number;
}

export interface ServiceTypeCreate {
  Code: string;
  Name: string;
  Description?: string;
  Priority?: number;
  AverageTimeMinutes?: number;
  TicketPrefix: string;
  Color?: string;
}

export interface ServiceTypeUpdate {
  Name?: string;
  Description?: string;
  Priority?: number;
  AverageTimeMinutes?: number;
  Color?: string;
  IsActive?: boolean;
}

export interface ServiceTypeListResponse {
  services: ServiceType[];
  total: number;
  active_count: number;
  inactive_count: number;
  average_wait_time?: number;
  priority_distribution?: { [key: number]: number };
}

export interface ServiceTypeStats {
  service_type_id: number;
  tickets_today: number;
  tickets_waiting: number;
  tickets_completed: number;
  average_wait_time: number;
  average_service_time: number;
  stations_assigned: number;
  stations_active: number;
  current_queue_size: number;
  estimated_wait_minutes: number;
}

export interface ServiceTypeDashboard {
  total_services: number;
  active_services: number;
  services_with_queues: number;
  total_tickets_today: number;
  average_wait_time_global: number;
  busiest_service?: {
    id: number;
    name: string;
    queue_size: number;
  };
  priority_breakdown: {
    priority: number;
    count: number;
    percentage: number;
  }[];
  hourly_distribution?: { [hour: string]: number };
}

export interface ServiceTypeSearchFilters {
  search_text?: string;
  active_only?: boolean;
  priority?: number;
  min_time?: number;
  max_time?: number;
  has_stations?: boolean;
}

export interface ServiceTypeQuickSetup {
  include_default_services?: boolean;
  custom_services?: ServiceTypeCreate[];
}

export interface BulkServiceTypeCreate {
  service_types: ServiceTypeCreate[];
}

export interface BulkServiceTypeResponse {
  created: ServiceType[];
  failed: {
    data: ServiceTypeCreate;
    error: string;
  }[];
  total_processed: number;
  success_count: number;
  failure_count: number;
}

export interface ServiceTypeValidation {
  field: string;
  value: string;
  is_valid: boolean;
  message?: string;
}
