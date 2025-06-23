# Agricultural and Environmental (46-50)

## 46. Precision Irrigation Controller

```python
class PrecisionIrrigationController:
    def __init__(self, field_config_path, weather_service=None, farm_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.field_config = FieldConfiguration(field_config_path)
        self.local_scheduler = LocalIrrigationScheduler(self.field_config)
        self.soil_sensors = SoilMoistureSensorArray()
        self.weather_stations = LocalWeatherStationArray()
        self.irrigation_controls = IrrigationControlSystem()
        
        # Try once to connect to weather service
        if weather_service and farm_id:
            try:
                self.service = AgriculturalWeatherService(weather_service, farm_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest weather forecast
                    self._sync_weather_forecast()
            except Exception:
                # No retry - stay with local scheduler
                self.service = None
    
    def optimize_irrigation(self):
        # Get sensor readings
        soil_moisture = self.soil_sensors.get_readings()
        local_weather = self.weather_stations.get_readings()
        
        # Always calculate locally first
        irrigation_plan = self.local_scheduler.calculate_irrigation(
            soil_moisture, local_weather)
        
        # Apply irrigation plan
        self.irrigation_controls.apply_plan(irrigation_plan)
        
        # If online, get enhanced weather data and recalculate
        if self.mode == "ONLINE":
            try:
                weather_forecast = self.service.get_weather_forecast()
                if weather_forecast:
                    enhanced_plan = self.local_scheduler.calculate_irrigation(
                        soil_moisture, local_weather, weather_forecast)
                    self.irrigation_controls.apply_plan(enhanced_plan)
                    irrigation_plan = enhanced_plan
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return irrigation_plan
```

## 47. Crop Health Monitoring System

```python
class CropHealthMonitor:
    def __init__(self, crop_db_path, agriculture_service=None, farm_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.crop_db = LocalCropDatabase(crop_db_path)
        self.local_analyzer = LocalCropAnalyzer()
        self.aerial_imaging = DroneImagingSystem()
        self.ground_sensors = PlantHealthSensorArray()
        self.treatment_system = CropTreatmentSystem()
        
        # Try once to connect to agriculture service
        if agriculture_service and farm_id:
            try:
                self.service = AgricultureService(agriculture_service, farm_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest crop disease models
                    self._sync_disease_models()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_crop_health(self, field_id):
        # Gather monitoring data
        aerial_images = self.aerial_imaging.capture_field(field_id)
        ground_data = self.ground_sensors.get_readings(field_id)
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_crop_health(
            aerial_images, ground_data, self.crop_db)
        
        # Store analysis results locally
        self.crop_db.store_analysis(field_id, analysis)
        
        # Generate treatment recommendations
        treatment_plan = self.local_analyzer.generate_treatment_plan(analysis)
        
        # If serious issues detected, apply treatments
        if analysis.requires_treatment:
            self.treatment_system.apply_treatment(treatment_plan)
        
        # If online, report to agriculture service
        if self.mode == "ONLINE":
            try:
                self.service.report_crop_data(field_id, aerial_images, ground_data)
                enhanced_plan = self.service.get_enhanced_treatment_plan(analysis)
                if enhanced_plan:
                    self.treatment_system.apply_treatment(enhanced_plan)
                    treatment_plan = enhanced_plan
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis, treatment_plan
```

## 48. Livestock Monitoring System

```python
class LivestockMonitor:
    def __init__(self, livestock_db_path, veterinary_service=None, farm_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.livestock_db = LocalLivestockDatabase(livestock_db_path)
        self.local_analyzer = LocalHealthAnalyzer()
        self.tracking_tags = LivestockTrackingSystem()
        self.biometric_sensors = LivestockBiometricSensors()
        self.alert_system = VeterinaryAlertSystem()
        
        # Try once to connect to veterinary service
        if veterinary_service and farm_id:
            try:
                self.service = VeterinaryService(veterinary_service, farm_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest health parameters
                    self._sync_health_parameters()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_livestock(self):
        # Get monitoring data
        location_data = self.tracking_tags.get_locations()
        biometric_data = self.biometric_sensors.get_readings()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_livestock_health(
            location_data, biometric_data, self.livestock_db)
        
        # Store data locally
        self.livestock_db.store_monitoring_data(location_data, biometric_data, analysis)
        
        # Handle any health issues
        if analysis.health_issues:
            self.alert_system.create_alerts(analysis.health_issues)
        
        # If online, report to veterinary service
        if self.mode == "ONLINE":
            try:
                self.service.report_livestock_data(location_data, biometric_data)
                if analysis.health_issues:
                    self.service.report_health_issues(analysis.health_issues)
                    recommendations = self.service.get_treatment_recommendations()
                    if recommendations:
                        self.alert_system.show_recommendations(recommendations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 49. Environmental Monitoring Station

```python
class EnvironmentalMonitor:
    def __init__(self, env_db_path, environment_service=None, station_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.env_db = LocalEnvironmentalDatabase(env_db_path)
        self.local_analyzer = LocalEnvironmentalAnalyzer()
        self.air_quality_sensors = AirQualitySensorArray()
        self.water_quality_sensors = WaterQualitySensorArray()
        self.weather_sensors = WeatherSensorArray()
        self.alert_system = EnvironmentalAlertSystem()
        
        # Try once to connect to environment service
        if environment_service and station_id:
            try:
                self.service = EnvironmentalMonitoringService(environment_service, station_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest threshold parameters
                    self._sync_environmental_thresholds()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_environment(self):
        # Get sensor readings
        air_data = self.air_quality_sensors.get_readings()
        water_data = self.water_quality_sensors.get_readings()
        weather_data = self.weather_sensors.get_readings()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_environmental_quality(
            air_data, water_data, weather_data, self.env_db.get_thresholds())
        
        # Store data locally
        self.env_db.store_readings(air_data, water_data, weather_data, analysis)
        
        # Handle any alerts for dangerous conditions
        if analysis.hazardous_conditions:
            self.alert_system.trigger_alerts(analysis.hazardous_conditions)
        
        # If online, report to environmental service
        if self.mode == "ONLINE":
            try:
                self.service.report_environmental_data(
                    air_data, water_data, weather_data)
                if analysis.hazardous_conditions:
                    self.service.report_hazardous_conditions(analysis.hazardous_conditions)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 50. Soil Composition Analyzer

```python
class SoilCompositionAnalyzer:
    def __init__(self, soil_db_path, agronomy_service=None, farm_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.soil_db = LocalSoilDatabase(soil_db_path)
        self.local_analyzer = LocalSoilAnalyzer()
        self.soil_sensors = SoilSensorArray()
        self.fertilizer_system = PrecisionFertilizerSystem()
        
        # Try once to connect to agronomy service
        if agronomy_service and farm_id:
            try:
                self.service = AgronomyService(agronomy_service, farm_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest soil health models
                    self._sync_soil_models()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def analyze_soil(self, field_id):
        # Get soil sensor readings
        soil_data = self.soil_sensors.get_readings(field_id)
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_soil_composition(
            soil_data, self.soil_db)
        
        # Store analysis locally
        self.soil_db.store_analysis(field_id, analysis)
        
        # Generate fertilization plan
        fertilizer_plan = self.local_analyzer.create_fertilizer_plan(analysis)
        
        # If deficiencies detected, apply fertilizer
        if analysis.requires_fertilizer:
            self.fertilizer_system.apply_fertilizer(field_id, fertilizer_plan)
        
        # If online, report to agronomy service
        if self.mode == "ONLINE":
            try:
                self.service.report_soil_data(field_id, soil_data, analysis)
                enhanced_plan = self.service.get_optimized_fertilizer_plan(analysis)
                if enhanced_plan:
                    self.fertilizer_system.apply_fertilizer(field_id, enhanced_plan)
                    fertilizer_plan = enhanced_plan
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis, fertilizer_plan
```

Each agricultural IoT application implements MCP Zero's offline-first resilience pattern:
1. All systems start in offline mode by default
2. Only one connection attempt is made to remote services
3. If connection fails or is lost later, systems permanently remain in offline mode
4. Local processing ensures critical agricultural functions continue regardless of connectivity
5. Vital operations like irrigation, crop health monitoring, and livestock tracking never depend on network availability
