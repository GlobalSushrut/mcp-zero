# Healthcare and Wearables (36-40)

## 36. Smart Prosthetic Controller

```python
class SmartProstheticController:
    def __init__(self, user_profile_path, health_service=None, device_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.user_profile = UserProfileDatabase(user_profile_path)
        self.local_controller = LocalProstheticController()
        self.emg_sensors = EMGSensorArray()
        self.position_sensors = PositionSensorArray()
        self.actuator_system = ProstheticActuatorSystem()
        
        # Try once to connect to health service
        if health_service and device_id:
            try:
                self.service = ProstheticHealthService(health_service, device_id)
                if self.service.authenticate(timeout=2):
                    self.mode = "ONLINE"
                    # Get latest movement models
                    self._sync_movement_models()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def process_movement_intent(self):
        # Get sensor readings
        emg_data = self.emg_sensors.get_readings()
        position_data = self.position_sensors.get_readings()
        
        # Always process locally first
        movement_command = self.local_controller.interpret_signals(
            emg_data, position_data, self.user_profile)
        
        # Execute the movement
        self.actuator_system.execute_movement(movement_command)
        
        # Store usage data locally
        self.user_profile.log_movement(movement_command, emg_data, position_data)
        
        # If online, report usage data
        if self.mode == "ONLINE":
            try:
                self.service.report_usage_data(emg_data, position_data, movement_command)
                model_updates = self.service.get_model_updates()
                if model_updates:
                    self.local_controller.update_models(model_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return movement_command
```

## 37. Fall Detection and Prevention System

```python
class FallDetectionSystem:
    def __init__(self, user_data_path, monitoring_service=None, user_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.user_data = UserDataStore(user_data_path)
        self.local_detector = LocalFallDetector()
        self.motion_sensors = MotionSensorArray()
        self.position_sensors = PositionSensorArray()
        self.alert_system = EmergencyAlertSystem()
        
        # Try once to connect to monitoring service
        if monitoring_service and user_id:
            try:
                self.service = FallMonitoringService(monitoring_service, user_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest detection parameters
                    self._sync_detection_parameters()
            except Exception:
                # No retry - stay with local detector
                self.service = None
    
    def monitor_movement(self):
        # Get sensor readings
        motion_data = self.motion_sensors.get_readings()
        position_data = self.position_sensors.get_readings()
        
        # Always analyze locally first
        analysis = self.local_detector.analyze_movement(
            motion_data, position_data, self.user_data)
        
        # Handle any detected falls or risks
        if analysis.fall_detected:
            self.alert_system.trigger_emergency_alert(analysis)
            self.user_data.log_fall_event(analysis)
        elif analysis.fall_risk:
            self.alert_system.trigger_warning(analysis)
        
        # If online, report to monitoring service
        if self.mode == "ONLINE":
            try:
                self.service.report_movement_data(motion_data, position_data)
                if analysis.fall_detected:
                    self.service.report_fall_event(analysis)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 38. Sleep Monitoring System

```python
class SleepMonitor:
    def __init__(self, user_data_path, health_service=None, user_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.user_data = SleepDataStore(user_data_path)
        self.local_analyzer = LocalSleepAnalyzer()
        self.motion_sensors = BedMotionSensorArray()
        self.biometric_sensors = BiometricSensorArray()
        self.environment_sensors = EnvironmentSensorArray()
        
        # Try once to connect to health service
        if health_service and user_id:
            try:
                self.service = SleepHealthService(health_service, user_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get personalized sleep model
                    self._sync_sleep_model()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_sleep(self):
        # Get sensor readings
        motion_data = self.motion_sensors.get_readings()
        biometric_data = self.biometric_sensors.get_readings()
        environment_data = self.environment_sensors.get_readings()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_sleep_quality(
            motion_data, biometric_data, environment_data)
        
        # Store sleep data locally
        self.user_data.store_sleep_data(analysis)
        
        # Process environmental improvements
        environment_actions = self.local_analyzer.suggest_environment_improvements(
            analysis, environment_data)
        
        # If online, report sleep data
        if self.mode == "ONLINE":
            try:
                self.service.report_sleep_data(motion_data, biometric_data, environment_data)
                recommendations = self.service.get_sleep_recommendations()
                if recommendations:
                    # Store personalized recommendations
                    self.user_data.store_recommendations(recommendations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 39. Cardiac Monitoring System

```python
class CardiacMonitor:
    def __init__(self, medical_record_path, cardiac_service=None, patient_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.medical_record = LocalMedicalRecord(medical_record_path)
        self.local_analyzer = LocalCardiacAnalyzer()
        self.ecg_sensor = ECGSensor()
        self.blood_pressure_sensor = BloodPressureSensor()
        self.alert_system = CardiacAlertSystem()
        
        # Try once to connect to cardiac service
        if cardiac_service and patient_id:
            try:
                self.service = CardiacMonitoringService(cardiac_service, patient_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get patient-specific parameters
                    self._sync_cardiac_parameters()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_cardiac_activity(self):
        # Get sensor readings
        ecg_data = self.ecg_sensor.get_reading()
        blood_pressure = self.blood_pressure_sensor.get_reading()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_cardiac_activity(
            ecg_data, blood_pressure, self.medical_record)
        
        # Store data locally
        self.medical_record.store_cardiac_data(ecg_data, blood_pressure, analysis)
        
        # Handle any cardiac events
        if analysis.requires_attention:
            self.alert_system.trigger_alert(analysis.severity, analysis.condition)
        
        # If online, report to cardiac service
        if self.mode == "ONLINE":
            try:
                self.service.report_cardiac_data(ecg_data, blood_pressure)
                if analysis.requires_attention:
                    self.service.report_cardiac_event(analysis)
                    response = self.service.get_emergency_instructions()
                    if response:
                        self.alert_system.display_instructions(response)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 40. Dietary Monitoring System

```python
class DietaryMonitor:
    def __init__(self, nutrition_db_path, health_service=None, user_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.nutrition_db = LocalNutritionDatabase(nutrition_db_path)
        self.local_analyzer = LocalNutritionAnalyzer()
        self.food_scanner = FoodScannerDevice()
        self.consumption_tracker = ConsumptionTracker()
        self.recommendation_engine = NutritionRecommendationEngine()
        
        # Try once to connect to health service
        if health_service and user_id:
            try:
                self.service = NutritionHealthService(health_service, user_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest nutrition guidelines
                    self._sync_nutrition_guidelines()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def track_meal(self, meal_data):
        # Get meal details from scanner or manual input
        if isinstance(meal_data, str) and meal_data == "scan":
            meal_data = self.food_scanner.scan_meal()
        
        # Always analyze locally first
        nutrition_analysis = self.local_analyzer.analyze_meal(
            meal_data, self.nutrition_db)
        
        # Track consumption
        self.consumption_tracker.record_meal(meal_data, nutrition_analysis)
        
        # Generate recommendations
        diet_plan = self.recommendation_engine.update_recommendations(
            self.consumption_tracker.get_history(), self.nutrition_db)
        
        # If online, report meal data
        if self.mode == "ONLINE":
            try:
                self.service.report_meal(meal_data, nutrition_analysis)
                enhanced_plan = self.service.get_personalized_plan()
                if enhanced_plan:
                    diet_plan = enhanced_plan
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return nutrition_analysis, diet_plan
```

Each healthcare and wearable IoT application implements MCP Zero's offline-first resilience pattern:
1. All systems start in offline mode by default
2. Only one connection attempt is made to remote services
3. Systems permanently revert to offline mode if connection fails or is lost
4. Local processing ensures critical functionality regardless of connectivity
5. Patient safety and health monitoring continue without disruption even when offline
