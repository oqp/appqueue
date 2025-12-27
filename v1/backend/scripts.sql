create database AppQueueMunoz collate SQL_Latin1_General_CP1_CI_AS
go

grant connect on database :: AppQueueMunoz to dbo
go

grant view any column encryption key definition, view any column master key definition on database :: AppQueueMunoz to [public]
go

create table dbo.MessageTemplates
(
    Id        int identity
        primary key,
    Name      nvarchar(100) not null
        unique,
    Type      nvarchar(20)  not null
        check ([Type] = 'Display' OR [Type] = 'Audio' OR [Type] = 'Email' OR [Type] = 'SMS'),
    Subject   nvarchar(200),
    Content   ntext         not null,
    Variables ntext,
    Language  nvarchar(5) default 'es',
    IsActive  bit         default 1,
    CreatedAt datetime2   default getdate()
)
go

create table dbo.Patients
(
    Id             uniqueidentifier default newid() not null
        primary key,
    DocumentNumber nvarchar(20)                     not null
        unique,
    FullName       nvarchar(200)                    not null,
    BirthDate      date                             not null,
    Gender         nvarchar(10)                     not null
        check ([Gender] = 'Otro' OR [Gender] = 'F' OR [Gender] = 'M'),
    Phone          nvarchar(20),
    Email          nvarchar(100),
    CreatedAt      datetime2        default getdate(),
    UpdatedAt      datetime2        default getdate(),
    IsActive       bit              default 1,
    Age            as datediff(year, [BirthDate], getdate())
)
go

create index IX_Patients_DocumentNumber
    on dbo.Patients (DocumentNumber)
go

create index IX_Patients_Phone
    on dbo.Patients (Phone)
go

create table dbo.Roles
(
    Id          int identity
        primary key,
    Name        nvarchar(50) not null
        unique,
    Description nvarchar(200),
    Permissions ntext,
    IsActive    bit       default 1,
    CreatedAt   datetime2 default getdate()
)
go

create table dbo.ServiceTypes
(
    Id                 int identity
        primary key,
    Code               nvarchar(10)  not null
        unique,
    Name               nvarchar(100) not null,
    Description        nvarchar(500),
    Priority           int         default 1
        check ([Priority] >= 1 AND [Priority] <= 5),
    AverageTimeMinutes int         default 10,
    TicketPrefix       nvarchar(5)   not null,
    Color              nvarchar(7) default '#007bff',
    IsActive           bit         default 1,
    CreatedAt          datetime2   default getdate()
)
go

create table dbo.Stations
(
    Id              int identity
        primary key,
    Name            nvarchar(100) not null,
    Code            nvarchar(10)  not null
        unique,
    Description     nvarchar(200),
    ServiceTypeId   int
        references dbo.ServiceTypes,
    Location        nvarchar(100),
    IsActive        bit          default 1,
    Status          nvarchar(20) default 'Available'
        check ([Status] = 'Offline' OR [Status] = 'Maintenance' OR [Status] = 'Break' OR [Status] = 'Busy' OR
               [Status] = 'Available'),
    CurrentTicketId uniqueidentifier,
    CreatedAt       datetime2    default getdate()
)
go

create table dbo.DailyMetrics
(
    Id                 uniqueidentifier default newid() not null
        primary key,
    Date               date                             not null,
    ServiceTypeId      int                              not null
        references dbo.ServiceTypes,
    StationId          int
        references dbo.Stations,
    TotalTickets       int              default 0,
    CompletedTickets   int              default 0,
    CancelledTickets   int              default 0,
    NoShowTickets      int              default 0,
    AverageWaitTime    decimal(5, 2)    default 0,
    AverageServiceTime decimal(5, 2)    default 0,
    PeakHour           nvarchar(5),
    CreatedAt          datetime2        default getdate()
)
go

create table dbo.Tickets
(
    Id                uniqueidentifier default newid() not null
        primary key,
    TicketNumber      nvarchar(20)                     not null,
    PatientId         uniqueidentifier                 not null
        references dbo.Patients,
    ServiceTypeId     int                              not null
        references dbo.ServiceTypes,
    StationId         int
        references dbo.Stations,
    Status            nvarchar(20)     default 'Waiting'
        check ([Status] = 'NoShow' OR [Status] = 'Cancelled' OR [Status] = 'Completed' OR [Status] = 'InProgress' OR
               [Status] = 'Called' OR [Status] = 'Waiting'),
    Position          int                              not null,
    EstimatedWaitTime int,
    QrCode            ntext,
    Notes             nvarchar(500),
    CreatedAt         datetime2        default getdate(),
    CalledAt          datetime2,
    AttendedAt        datetime2,
    CompletedAt       datetime2,
    ActualWaitTime    as datediff(minute, [CreatedAt], isnull([AttendedAt], getdate())),
    ServiceTime       as datediff(minute, [AttendedAt], [CompletedAt])
)
go

create table dbo.NotificationLog
(
    Id           uniqueidentifier default newid() not null
        primary key,
    TicketId     uniqueidentifier                 not null
        references dbo.Tickets,
    Type         nvarchar(20)                     not null
        check ([Type] = 'Audio' OR [Type] = 'Push' OR [Type] = 'Email' OR [Type] = 'SMS'),
    Recipient    nvarchar(100)                    not null,
    Message      ntext                            not null,
    Status       nvarchar(20)     default 'Pending'
        check ([Status] = 'Delivered' OR [Status] = 'Failed' OR [Status] = 'Sent' OR [Status] = 'Pending'),
    ErrorMessage nvarchar(500),
    SentAt       datetime2,
    CreatedAt    datetime2        default getdate()
)
go

create index IX_NotificationLog_Status
    on dbo.NotificationLog (Status)
go

create table dbo.QueueState
(
    Id              int identity
        primary key,
    ServiceTypeId   int not null
        references dbo.ServiceTypes,
    StationId       int
        references dbo.Stations,
    CurrentTicketId uniqueidentifier
        references dbo.Tickets,
    NextTicketId    uniqueidentifier
        references dbo.Tickets,
    QueueLength     int       default 0,
    AverageWaitTime int       default 0,
    LastUpdateAt    datetime2 default getdate()
)
go

create index IX_Tickets_Status
    on dbo.Tickets (Status)
go

create index IX_Tickets_ServiceType
    on dbo.Tickets (ServiceTypeId)
go

create index IX_Tickets_CreatedAt
    on dbo.Tickets (CreatedAt)
go

create index IX_Tickets_Station
    on dbo.Tickets (StationId)
go

create index IX_Tickets_PatientId
    on dbo.Tickets (PatientId)
go

create table dbo.Users
(
    Id           uniqueidentifier default newid() not null
        primary key,
    Username     nvarchar(50)                     not null
        unique,
    Email        nvarchar(100)                    not null
        unique,
    PasswordHash nvarchar(255)                    not null,
    FullName     nvarchar(200)                    not null,
    RoleId       int                              not null
        references dbo.Roles,
    StationId    int
        references dbo.Stations,
    IsActive     bit              default 1,
    LastLogin    datetime2,
    CreatedAt    datetime2        default getdate(),
    UpdatedAt    datetime2        default getdate()
)
go

create table dbo.ActivityLog
(
    Id        uniqueidentifier default newid() not null
        primary key,
    UserId    uniqueidentifier
        references dbo.Users,
    TicketId  uniqueidentifier
        references dbo.Tickets,
    StationId int
        references dbo.Stations,
    Action    nvarchar(50)                     not null,
    Details   ntext,
    IpAddress nvarchar(45),
    UserAgent nvarchar(500),
    CreatedAt datetime2        default getdate()
)
go

create index IX_ActivityLog_Action
    on dbo.ActivityLog (Action)
go

create index IX_ActivityLog_CreatedAt
    on dbo.ActivityLog (CreatedAt)
go
