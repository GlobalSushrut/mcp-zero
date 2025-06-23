# Smart Home and Building Automation (6-10)

## 6. Water Leak Detection System

```python
class LeakDetectionSystem:
    def __init__(self, sensor_config_path, monitoring_service=None, home_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.config = SensorConfig(sensor_config_path)
        self.local_processor = LocalLeakProcessor()
        self.moisture_sensors = MoistureSensorArray()
        self.water_shutoff = WaterShutoffValve()
        
        # Try once to connect to monitoring service
        if monitoring_service and home_id:
            try:
                self.service = WaterMonitoringService(monitoring_service, home_id)
                if self.service.register_device(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local processor
                self.service = None
    
    def check_for_leaks(self):
        # Get readings from all moisture sensors
        readings = self.moisture_sensors.get_readings()
        
        # Always process locally first
        leak_detected, location = self.local_processor.analyze_readings(readings)
        
        # Take immediate action if leak detected
        if leak_detected:
            self.water_shutoff.close_valve()
            self.local_processor.log_leak_event(location)
        
        # If online, report to monitoring service
        if self.mode == "ONLINE" and leak_detected:
            try:
                self.service.report_leak(location, readings)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
```

## 7. Smart Energy Monitor

```python
class EnergyMonitor:
    def __init__(self, local_db_path, energy_service=None, home_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalEnergyDatabase(local_db_path)
        self.local_analyzer = LocalEnergyAnalyzer()
        self.energy_sensors = EnergySensorArray()
        
        # Try once to connect to energy service
        if energy_service and home_id:
            try:
                self.service = EnergyMonitoringService(energy_service, home_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_energy_usage(self):
        # Collect energy usage data
        usage_data = self.energy_sensors.collect_data()
        
        # Always store and analyze locally
        self.local_db.store_readings(usage_data)
        insights = self.local_analyzer.analyze_usage(self.local_db)
        
        # If online, send data to service
        if self.mode == "ONLINE":
            try:
                self.service.report_usage(usage_data)
                cloud_insights = self.service.get_insights()
                if cloud_insights:
                    # Enhance local insights with cloud insights
                    insights.update(cloud_insights)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
                
        return insights
```

## 8. Smart Irrigation Controller

```python
class IrrigationController:
    def __init__(self, garden_config_path, weather_service=None, location_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.garden_config = GardenConfig(garden_config_path)
        self.local_scheduler = LocalIrrigationScheduler(self.garden_config)
        self.moisture_sensors = SoilMoistureSensorArray()
        self.irrigation_valves = IrrigationValveArray()
        
        # Try once to connect to weather service
        if weather_service and location_id:
            try:
                self.weather = WeatherService(weather_service, location_id)
                if self.weather.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local scheduler
                self.weather = None
    
    def update_irrigation_schedule(self):
        # Get current soil moisture readings
        moisture_levels = self.moisture_sensors.get_readings()
        
        # Always calculate schedule locally first
        schedule = self.local_scheduler.calculate_schedule(moisture_levels)
        
        # If online, enhance schedule with weather forecast
        if self.mode == "ONLINE":
            try:
                forecast = self.weather.get_forecast()
                if forecast:
                    schedule = self.local_scheduler.adjust_for_weather(schedule, forecast)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.weather = None
        
        # Apply the irrigation schedule
        self.irrigation_valves.apply_schedule(schedule)
        return schedule
```

## 9. Indoor Air Quality Monitor

```python
class AirQualityMonitor:
    def __init__(self, thresholds_path, air_service=None, device_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.thresholds = AirQualityThresholds(thresholds_path)
        self.local_analyzer = LocalAirQualityAnalyzer(self.thresholds)
        self.sensors = AirQualitySensorArray()
        self.ventilation = VentilationController()
        
        # Try once to connect to air quality service
        if air_service and device_id:
            try:
                self.service = AirQualityService(air_service, device_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_air_quality(self):
        # Get readings from air quality sensors
        readings = self.sensors.get_readings()
        
        # Always analyze locally
        analysis = self.local_analyzer.analyze(readings)
        
        # Take action based on analysis
        if analysis.requires_ventilation:
            self.ventilation.increase_airflow(analysis.recommended_level)
        
        # If online, report to air quality service
        if self.mode == "ONLINE":
            try:
                self.service.report_readings(readings)
                recommendations = self.service.get_recommendations(readings)
                if recommendations:
                    # Apply any enhanced recommendations
                    self.ventilation.apply_recommendations(recommendations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
                
        return analysis
```

## 10. Smart Window and Shade Controller

```python
class WindowShadeController:
    def __init__(self, preference_path, weather_service=None, home_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.preferences = UserPreferences(preference_path)
        self.local_controller = LocalShadeController(self.preferences)
        self.light_sensors = LightSensorArray()
        self.temperature_sensors = TemperatureSensorArray()
        self.shade_motors = ShadeMotorArray()
        
        # Try once to connect to weather service
        if weather_service and home_id:
            try:
                self.weather = WeatherService(weather_service, home_id)
                if self.weather.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local controller
                self.weather = None
    
    def adjust_shades(self):
        # Get current readings
        light_levels = self.light_sensors.get_readings()
        temperatures = self.temperature_sensors.get_readings()
        
        # Always calculate locally first
        shade_positions = self.local_controller.calculate_positions(
            light_levels, temperatures)
        
        # If online, enhance with weather data
        if self.mode == "ONLINE":
            try:
                forecast = self.weather.get_short_term_forecast()
                if forecast:
                    shade_positions = self.local_controller.adjust_for_weather(
                        shade_positions, forecast)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.weather = None
        
        # Apply the calculated positions
        self.shade_motors.set_positions(shade_positions)
        return shade_positions
```

Each smart home system implements MCP Zero's offline-first resilience pattern with:
1. Default initialization in offline mode
2. Single connection attempt to remote services
3. Permanent fallback to offline mode on connection failure
4. Local processing that ensures functionality regardless of connectivity
