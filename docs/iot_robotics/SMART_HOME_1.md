# Smart Home and Building Automation (1-5)

## 1. Smart Thermostat Controller

```python
class SmartThermostat:
    def __init__(self, config_path, cloud_service=None, device_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.config = ThermostatConfig(config_path)
        self.local_controller = LocalTemperatureController()
        self.sensors = TemperatureSensorArray()
        
        # Try once to connect to cloud service
        if cloud_service and device_id:
            try:
                self.cloud = ThermostatCloudService(cloud_service, device_id)
                if self.cloud.authenticate(timeout=2):
                    self.mode = "ONLINE"
                    # Get latest settings but don't depend on them
                    self._sync_settings()
            except Exception:
                # No retry - stay with local controller
                self.cloud = None
    
    def update_temperature(self):
        current_temp = self.sensors.get_temperature()
        if self.mode == "ONLINE":
            try:
                # Try to send data to cloud
                self.cloud.report_temperature(current_temp)
            except Exception:
                # On any failure, revert to offline mode permanently
                self.mode = "OFFLINE"
                self.cloud = None
        
        # Always process locally regardless of mode
        self.local_controller.process_reading(current_temp)
```

## 2. Smart Lighting System

```python
class SmartLightingSystem:
    def __init__(self, home_layout_path, hub_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.layout = HomeLayout(home_layout_path)
        self.local_controller = LocalLightingController(self.layout)
        self.motion_sensors = MotionSensorArray()
        self.light_controls = LightControlArray()
        
        # Try once to connect to lighting hub
        if hub_url and api_key:
            try:
                self.hub = LightingHub(hub_url, api_key)
                if self.hub.connect(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local controller
                self.hub = None
    
    def process_motion_event(self, location):
        # Always handle locally first
        lighting_action = self.local_controller.get_lighting_action(location)
        self.light_controls.apply_action(lighting_action)
        
        # If online, also inform the hub
        if self.mode == "ONLINE":
            try:
                self.hub.report_motion(location)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.hub = None
```

## 3. Home Security Monitor

```python
class SecurityMonitor:
    def __init__(self, security_config_path, monitoring_service=None, home_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.config = SecurityConfig(security_config_path)
        self.local_monitor = LocalSecurityMonitor(self.config)
        self.sensors = SecuritySensorArray()
        self.alarm = SecurityAlarm()
        
        # Try once to connect to monitoring service
        if monitoring_service and home_id:
            try:
                self.service = MonitoringService(monitoring_service, home_id)
                if self.service.register_device(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local monitor
                self.service = None
    
    def handle_security_event(self, event_type, location):
        # Always process locally
        response = self.local_monitor.process_event(event_type, location)
        if response.alarm_triggered:
            self.alarm.trigger(response.alarm_level)
        
        # If online, notify the monitoring service
        if self.mode == "ONLINE":
            try:
                self.service.report_event(event_type, location)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
```

## 4. Smart Door Lock

```python
class SmartLock:
    def __init__(self, authorized_users_path, access_service=None, lock_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.users = AuthorizedUserDatabase(authorized_users_path)
        self.local_auth = LocalAuthenticationSystem()
        self.lock_mechanism = LockMechanism()
        self.access_log = LocalAccessLog()
        
        # Try once to connect to access service
        if access_service and lock_id:
            try:
                self.service = AccessControlService(access_service, lock_id)
                if self.service.authenticate(timeout=2):
                    self.mode = "ONLINE"
                    # Get latest authorized users
                    self._sync_authorized_users()
            except Exception:
                # No retry - stay with local authentication
                self.service = None
    
    def process_access_request(self, credentials):
        # Always verify locally
        access_granted = self.local_auth.verify_credentials(credentials, self.users)
        
        if access_granted:
            self.lock_mechanism.unlock()
            self.access_log.record_access(credentials, "Granted")
        else:
            self.access_log.record_access(credentials, "Denied")
        
        # If online, report the access attempt
        if self.mode == "ONLINE":
            try:
                self.service.report_access_attempt(credentials, access_granted)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return access_granted
```

## 5. HVAC Optimization System

```python
class HVACOptimizer:
    def __init__(self, building_model_path, energy_service=None, building_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.building_model = BuildingModel(building_model_path)
        self.local_optimizer = LocalHVACOptimizer()
        self.temperature_sensors = TemperatureSensorNetwork()
        self.hvac_controls = HVACControlSystem()
        
        # Try once to connect to energy service
        if energy_service and building_id:
            try:
                self.service = EnergyOptimizationService(energy_service, building_id)
                if self.service.connect(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest optimization parameters
                    self._update_optimization_parameters()
            except Exception:
                # No retry - stay with local optimizer
                self.service = None
    
    def optimize_hvac(self):
        # Collect temperature data
        temp_data = self.temperature_sensors.collect_data()
        
        # Always optimize locally
        settings = self.local_optimizer.calculate_optimal_settings(
            temp_data, self.building_model)
        
        # Apply the calculated settings
        self.hvac_controls.apply_settings(settings)
        
        # If online, send data and get enhanced optimization
        if self.mode == "ONLINE":
            try:
                enhanced_settings = self.service.get_enhanced_optimization(
                    temp_data, settings)
                # Apply enhanced settings if available
                if enhanced_settings:
                    self.hvac_controls.apply_settings(enhanced_settings)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
```

Each of these smart home applications follows MCP Zero's offline-first resilience pattern by starting offline by default, attempting connection only once, and permanently falling back to offline mode on connection failure.
