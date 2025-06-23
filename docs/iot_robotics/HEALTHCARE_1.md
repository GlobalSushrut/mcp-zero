# Healthcare and Wearables (31-35)

## 31. Patient Monitoring System

```python
class PatientMonitoringSystem:
    def __init__(self, patient_db_path, health_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.patient_db = LocalPatientDatabase(patient_db_path)
        self.local_analyzer = LocalHealthAnalyzer()
        self.vital_sensors = VitalSignSensorArray()
        self.alert_system = ClinicalAlertSystem()
        
        # Try once to connect to health service
        if health_service and facility_id:
            try:
                self.service = HealthMonitoringService(health_service, facility_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest patient thresholds
                    self._sync_patient_thresholds()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_patient(self, patient_id):
        # Get vital sign readings
        vitals = self.vital_sensors.get_patient_readings(patient_id)
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_vitals(
            vitals, self.patient_db.get_thresholds(patient_id))
        
        # Store readings locally
        self.patient_db.store_readings(patient_id, vitals)
        
        # Handle any alerts
        if analysis.requires_attention:
            self.alert_system.create_alert(
                patient_id, analysis.severity, analysis.condition)
        
        # If online, report to health service
        if self.mode == "ONLINE":
            try:
                self.service.report_vitals(patient_id, vitals)
                recommendations = self.service.get_care_recommendations(patient_id)
                if recommendations:
                    # Store and process recommendations
                    self.patient_db.store_recommendations(patient_id, recommendations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 32. Medication Dispensing System

```python
class MedicationDispensingSystem:
    def __init__(self, medication_db_path, pharmacy_service=None, device_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.medication_db = LocalMedicationDatabase(medication_db_path)
        self.local_scheduler = LocalMedicationScheduler()
        self.dispensing_mechanism = DispensingMechanism()
        self.verification_system = MedicationVerificationSystem()
        
        # Try once to connect to pharmacy service
        if pharmacy_service and device_id:
            try:
                self.service = PharmacyService(pharmacy_service, device_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync medication schedules
                    self._sync_schedules()
            except Exception:
                # No retry - stay with local scheduler
                self.service = None
    
    def process_medication_request(self, patient_id, time):
        # Get patient's medication schedule
        schedule = self.medication_db.get_schedule(patient_id)
        
        # Always verify locally first
        medications = self.local_scheduler.get_due_medications(patient_id, schedule, time)
        
        if medications:
            # Verify medications before dispensing
            verified = self.verification_system.verify_medications(medications)
            if verified:
                self.dispensing_mechanism.dispense(medications)
                self.medication_db.log_dispensed(patient_id, medications, time)
        
        # If online, report dispensing activity
        if self.mode == "ONLINE":
            try:
                self.service.report_dispensing(patient_id, medications, time)
                schedule_updates = self.service.get_schedule_updates(patient_id)
                if schedule_updates:
                    self.medication_db.update_schedule(patient_id, schedule_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return medications
```

## 33. Fitness Tracking System

```python
class FitnessTrackingSystem:
    def __init__(self, user_data_path, health_service=None, user_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.user_data = LocalUserDatabase(user_data_path)
        self.local_analyzer = LocalFitnessAnalyzer()
        self.motion_sensors = MotionSensorArray()
        self.heart_rate_sensor = HeartRateSensor()
        self.user_interface = FitnessUI()
        
        # Try once to connect to health service
        if health_service and user_id:
            try:
                self.service = FitnessService(health_service, user_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync user profile
                    self._sync_user_profile()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def track_activity(self, activity_type):
        # Get sensor readings
        motion_data = self.motion_sensors.get_readings()
        heart_rate = self.heart_rate_sensor.get_reading()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_activity(
            activity_type, motion_data, heart_rate)
        
        # Store activity data locally
        self.user_data.store_activity(activity_type, analysis)
        
        # Update user interface
        self.user_interface.update_stats(analysis)
        
        # If online, report to fitness service
        if self.mode == "ONLINE":
            try:
                self.service.report_activity(activity_type, motion_data, heart_rate)
                insights = self.service.get_fitness_insights()
                if insights:
                    # Update UI with additional insights
                    self.user_interface.show_insights(insights)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 34. Medical Equipment Tracking

```python
class MedicalEquipmentTracker:
    def __init__(self, inventory_db_path, tracking_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.inventory_db = LocalInventoryDatabase(inventory_db_path)
        self.local_tracker = LocalEquipmentTracker()
        self.location_sensors = LocationSensorArray()
        self.usage_monitors = UsageMonitorArray()
        
        # Try once to connect to tracking service
        if tracking_service and facility_id:
            try:
                self.service = EquipmentTrackingService(tracking_service, facility_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync inventory data
                    self._sync_inventory()
            except Exception:
                # No retry - stay with local tracker
                self.service = None
    
    def track_equipment(self):
        # Get tracking data
        location_data = self.location_sensors.get_readings()
        usage_data = self.usage_monitors.get_readings()
        
        # Always process locally first
        updates = self.local_tracker.process_readings(location_data, usage_data)
        self.inventory_db.apply_updates(updates)
        
        # Generate utilization report
        report = self.local_tracker.generate_utilization_report(self.inventory_db)
        
        # If online, report to tracking service
        if self.mode == "ONLINE":
            try:
                self.service.report_equipment_status(location_data, usage_data)
                inventory_updates = self.service.get_inventory_updates()
                if inventory_updates:
                    self.inventory_db.apply_external_updates(inventory_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return report
```

## 35. Remote Patient Monitoring

```python
class RemotePatientMonitor:
    def __init__(self, patient_data_path, telehealth_service=None, device_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.patient_data = LocalPatientData(patient_data_path)
        self.local_analyzer = LocalHealthAnalyzer()
        self.vital_sensors = VitalSensorArray()
        self.medication_tracker = MedicationTracker()
        self.alert_system = PatientAlertSystem()
        
        # Try once to connect to telehealth service
        if telehealth_service and device_id:
            try:
                self.service = TelehealthService(telehealth_service, device_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest care plan
                    self._sync_care_plan()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_health(self, patient_id):
        # Get health data
        vitals = self.vital_sensors.get_readings()
        medication_adherence = self.medication_tracker.check_adherence()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_health(
            vitals, medication_adherence, self.patient_data.get_thresholds(patient_id))
        
        # Store data locally
        self.patient_data.store_readings(patient_id, vitals, medication_adherence)
        
        # Handle any alerts
        if analysis.requires_attention:
            self.alert_system.create_alert(
                patient_id, analysis.severity, analysis.condition)
        
        # If online, report to telehealth service
        if self.mode == "ONLINE":
            try:
                self.service.report_health_data(patient_id, vitals, medication_adherence)
                recommendations = self.service.get_recommendations()
                if recommendations:
                    # Process any care recommendations
                    self._process_recommendations(recommendations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

Each healthcare and wearable IoT application follows MCP Zero's offline-first resilience pattern:
1. All systems initialize in offline mode by default
2. Only a single connection attempt is made to remote services
3. Systems maintain full functionality through local processing when offline
4. If connection fails initially or is lost later, systems permanently remain in offline mode
5. Critical health monitoring and alerts continue to function without network connectivity
