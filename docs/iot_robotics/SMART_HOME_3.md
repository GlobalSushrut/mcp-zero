# Smart Home and Building Automation (11-15)

## 11. Smart Appliance Coordinator

```python
class ApplianceCoordinator:
    def __init__(self, appliance_config_path, grid_service=None, home_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.appliance_config = ApplianceConfig(appliance_config_path)
        self.local_scheduler = LocalApplianceScheduler(self.appliance_config)
        self.power_monitor = PowerMonitor()
        self.appliance_controllers = ApplianceControllerArray()
        
        # Try once to connect to grid service
        if grid_service and home_id:
            try:
                self.grid = SmartGridService(grid_service, home_id)
                if self.grid.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local scheduler
                self.grid = None
    
    def optimize_appliance_usage(self):
        # Get current power usage
        power_data = self.power_monitor.get_readings()
        
        # Always optimize locally first
        schedule = self.local_scheduler.create_schedule(power_data)
        
        # If online, enhance with grid data
        if self.mode == "ONLINE":
            try:
                grid_info = self.grid.get_pricing_and_load()
                if grid_info:
                    schedule = self.local_scheduler.adjust_for_grid(
                        schedule, grid_info)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.grid = None
        
        # Apply the schedule to appliances
        self.appliance_controllers.apply_schedule(schedule)
        return schedule
```

## 12. Access Control System

```python
class AccessControlSystem:
    def __init__(self, user_db_path, identity_service=None, building_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.user_db = LocalUserDatabase(user_db_path)
        self.local_authenticator = LocalIdentityVerifier()
        self.access_points = AccessPointArray()
        self.access_log = LocalAccessLog()
        
        # Try once to connect to identity service
        if identity_service and building_id:
            try:
                self.service = IdentityService(identity_service, building_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest access rules
                    self._sync_access_rules()
            except Exception:
                # No retry - stay with local authenticator
                self.service = None
    
    def process_access_request(self, credentials, access_point_id):
        # Always verify locally first
        access_granted = self.local_authenticator.verify_access(
            credentials, access_point_id, self.user_db)
        
        # Log the access attempt
        self.access_log.record_attempt(credentials, access_point_id, access_granted)
        
        # If access granted, unlock the door
        if access_granted:
            self.access_points.grant_access(access_point_id)
        
        # If online, report the access attempt
        if self.mode == "ONLINE":
            try:
                self.service.report_access_attempt(
                    credentials, access_point_id, access_granted)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return access_granted
```

## 13. Smart Waste Management

```python
class SmartWasteSystem:
    def __init__(self, bin_config_path, waste_service=None, building_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.bin_config = BinConfiguration(bin_config_path)
        self.local_optimizer = LocalCollectionOptimizer()
        self.fill_sensors = FillLevelSensorArray()
        self.bin_controls = BinControlArray()
        
        # Try once to connect to waste service
        if waste_service and building_id:
            try:
                self.service = WasteManagementService(waste_service, building_id)
                if self.service.connect(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local optimizer
                self.service = None
    
    def monitor_waste_levels(self):
        # Get current fill levels
        fill_levels = self.fill_sensors.get_readings()
        
        # Always process locally
        collection_schedule = self.local_optimizer.calculate_schedule(fill_levels)
        self.bin_controls.set_compaction_levels(
            self.local_optimizer.calculate_compaction(fill_levels))
        
        # If online, report fill levels and get enhanced schedule
        if self.mode == "ONLINE":
            try:
                self.service.report_fill_levels(fill_levels)
                enhanced_schedule = self.service.get_optimized_schedule(fill_levels)
                if enhanced_schedule:
                    collection_schedule = enhanced_schedule
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return collection_schedule
```

## 14. Occupancy-Based Climate Control

```python
class OccupancyClimateControl:
    def __init__(self, zone_config_path, building_service=None, building_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.zone_config = ZoneConfiguration(zone_config_path)
        self.local_controller = LocalClimateController(self.zone_config)
        self.occupancy_sensors = OccupancySensorArray()
        self.temperature_sensors = TemperatureSensorArray()
        self.climate_controls = ClimateControlArray()
        
        # Try once to connect to building service
        if building_service and building_id:
            try:
                self.service = BuildingManagementService(building_service, building_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def update_climate_settings(self):
        # Get current readings
        occupancy = self.occupancy_sensors.get_readings()
        temperatures = self.temperature_sensors.get_readings()
        
        # Always calculate locally first
        settings = self.local_controller.calculate_settings(occupancy, temperatures)
        
        # If online, report data and get enhanced settings
        if self.mode == "ONLINE":
            try:
                self.service.report_zone_data(occupancy, temperatures)
                enhanced_settings = self.service.get_optimized_settings()
                if enhanced_settings:
                    settings = self.local_controller.merge_settings(settings, enhanced_settings)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        # Apply the calculated settings
        self.climate_controls.apply_settings(settings)
        return settings
```

## 15. Emergency Response System

```python
class EmergencyResponseSystem:
    def __init__(self, emergency_config_path, response_service=None, building_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.config = EmergencyConfiguration(emergency_config_path)
        self.local_coordinator = LocalEmergencyCoordinator(self.config)
        self.alarm_sensors = EmergencySensorArray()
        self.notification_system = NotificationSystem()
        self.building_controls = BuildingControlSystem()
        
        # Try once to connect to response service
        if response_service and building_id:
            try:
                self.service = EmergencyResponseService(response_service, building_id)
                if self.service.register_device(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local coordinator
                self.service = None
    
    def handle_emergency_event(self, event_type, location):
        # Always process locally first
        response_plan = self.local_coordinator.create_response_plan(event_type, location)
        
        # Execute the response plan
        self.notification_system.send_alerts(response_plan.alerts)
        self.building_controls.execute_commands(response_plan.building_commands)
        
        # If online, report to emergency services
        if self.mode == "ONLINE":
            try:
                self.service.report_emergency(event_type, location, response_plan)
                external_instructions = self.service.get_external_instructions()
                if external_instructions:
                    self.notification_system.send_external_instructions(external_instructions)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return response_plan
```

Each of these systems demonstrates MCP Zero's offline-first resilience pattern where:
1. All systems start in offline mode by default
2. Only one connection attempt is made to remote services
3. If connection fails or is later lost, systems permanently remain in offline mode
4. Local processing ensures critical functionality continues regardless of connectivity
