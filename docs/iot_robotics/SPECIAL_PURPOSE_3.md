# Special Purpose IoT (96-100)

## 96. Space Habitat Monitoring System

```python
class SpaceHabitatMonitor:
    def __init__(self, habitat_db_path, mission_service=None, habitat_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.habitat_db = LocalHabitatDatabase(habitat_db_path)
        self.local_controller = LocalHabitatController()
        self.environmental_sensors = EnvironmentalSensorArray()
        self.life_support_sensors = LifeSupportSensorArray()
        self.radiation_sensors = RadiationSensorArray()
        self.alert_system = HabitatAlertSystem()
        
        # Try once to connect to mission service
        if mission_service and habitat_id:
            try:
                self.service = SpaceMissionService(mission_service, habitat_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest habitat parameters
                    self._sync_habitat_parameters()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def monitor_habitat_conditions(self):
        # Get sensor readings
        environmental_data = self.environmental_sensors.get_readings()
        life_support_data = self.life_support_sensors.get_readings()
        radiation_data = self.radiation_sensors.get_readings()
        
        # Always analyze locally first
        habitat_analysis = self.local_controller.analyze_habitat_conditions(
            environmental_data, life_support_data, radiation_data)
        
        # Generate life support adjustments
        adjustments = self.local_controller.calculate_life_support_adjustments(
            habitat_analysis)
        self.local_controller.apply_adjustments(adjustments)
        
        # Store monitoring data locally
        self.habitat_db.store_monitoring_data(
            environmental_data, life_support_data, 
            radiation_data, habitat_analysis, adjustments)
        
        # Handle any habitat warnings or emergencies
        if habitat_analysis.warnings:
            self.alert_system.issue_warnings(habitat_analysis.warnings)
            
        if habitat_analysis.critical_alerts:
            self.alert_system.trigger_emergency_protocols(habitat_analysis.critical_alerts)
        
        # If online, report to mission service
        if self.mode == "ONLINE":
            try:
                self.service.report_habitat_data(
                    environmental_data, life_support_data, 
                    radiation_data, habitat_analysis)
                
                if habitat_analysis.warnings or habitat_analysis.critical_alerts:
                    response_protocols = self.service.get_response_protocols()
                    if response_protocols:
                        self.alert_system.update_protocols(response_protocols)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return habitat_analysis, adjustments
```

## 97. Museum Artifact Preservation System

```python
class MuseumPreservationSystem:
    def __init__(self, preservation_db_path, museum_service=None, gallery_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.preservation_db = LocalPreservationDatabase(preservation_db_path)
        self.local_controller = LocalPreservationController()
        self.environmental_sensors = EnvironmentalSensorArray()
        self.light_sensors = LightSensorArray()
        self.vibration_sensors = VibrationSensorArray()
        self.climate_control = ClimateControlSystem()
        
        # Try once to connect to museum service
        if museum_service and gallery_id:
            try:
                self.service = MuseumPreservationService(museum_service, gallery_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest preservation parameters
                    self._sync_preservation_parameters()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def monitor_preservation_conditions(self):
        # Get sensor readings
        environmental_data = self.environmental_sensors.get_readings()
        light_data = self.light_sensors.get_readings()
        vibration_data = self.vibration_sensors.get_readings()
        
        # Always analyze locally first
        preservation_analysis = self.local_controller.analyze_conditions(
            environmental_data, light_data, vibration_data)
        
        # Generate climate control adjustments
        adjustments = self.local_controller.calculate_climate_adjustments(
            preservation_analysis)
        
        # Apply adjustments to maintain optimal conditions
        self.climate_control.apply_adjustments(adjustments)
        
        # Store monitoring data locally
        self.preservation_db.store_monitoring_data(
            environmental_data, light_data, 
            vibration_data, preservation_analysis, adjustments)
        
        # If online, report to museum service
        if self.mode == "ONLINE":
            try:
                self.service.report_preservation_data(
                    environmental_data, light_data, 
                    vibration_data, preservation_analysis)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return preservation_analysis, adjustments
```

## 98. Underwater Research Platform

```python
class UnderwaterResearchPlatform:
    def __init__(self, research_db_path, ocean_service=None, platform_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.research_db = LocalUnderwaterDatabase(research_db_path)
        self.local_controller = LocalUnderwaterController()
        self.water_sensors = WaterSensorArray()
        self.sonar_system = SonarSystem()
        self.imaging_system = UnderwaterImagingSystem()
        self.sample_collector = SampleCollectionSystem()
        
        # Try once to connect to ocean service
        if ocean_service and platform_id:
            try:
                self.service = OceanResearchService(ocean_service, platform_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest research parameters
                    self._sync_research_parameters()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def conduct_underwater_research(self, coordinates):
        # Get sensor data
        water_data = self.water_sensors.get_readings()
        sonar_data = self.sonar_system.scan_area(coordinates)
        image_data = self.imaging_system.capture_images(coordinates)
        
        # Always analyze locally first
        underwater_analysis = self.local_controller.analyze_underwater_data(
            water_data, sonar_data, image_data, coordinates)
        
        # Determine if samples should be collected
        if self.local_controller.should_collect_samples(underwater_analysis):
            sample_results = self.sample_collector.collect_samples(
                coordinates, underwater_analysis.collection_points)
            underwater_analysis.sample_results = sample_results
        
        # Store research data locally
        self.research_db.store_research_data(
            coordinates, water_data, sonar_data, 
            image_data, underwater_analysis)
        
        # If online, report to ocean service
        if self.mode == "ONLINE":
            try:
                self.service.report_research_data(
                    coordinates, water_data, sonar_data, 
                    image_data, underwater_analysis)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return underwater_analysis
```

## 99. Nuclear Facility Monitoring System

```python
class NuclearFacilityMonitor:
    def __init__(self, facility_db_path, regulatory_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.facility_db = LocalFacilityDatabase(facility_db_path)
        self.local_analyzer = LocalNuclearAnalyzer()
        self.radiation_sensors = RadiationSensorArray()
        self.temperature_sensors = TemperatureSensorArray()
        self.pressure_sensors = PressureSensorArray()
        self.safety_system = NuclearSafetySystem()
        
        # Try once to connect to regulatory service
        if regulatory_service and facility_id:
            try:
                self.service = NuclearRegulatoryService(regulatory_service, facility_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest safety parameters
                    self._sync_safety_parameters()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_nuclear_conditions(self):
        # Get sensor readings
        radiation_data = self.radiation_sensors.get_readings()
        temperature_data = self.temperature_sensors.get_readings()
        pressure_data = self.pressure_sensors.get_readings()
        
        # Always analyze locally first
        facility_analysis = self.local_analyzer.analyze_facility_conditions(
            radiation_data, temperature_data, pressure_data)
        
        # Store monitoring data locally
        self.facility_db.store_monitoring_data(
            radiation_data, temperature_data, 
            pressure_data, facility_analysis)
        
        # Handle any safety issues
        if facility_analysis.warnings:
            self.safety_system.issue_warnings(facility_analysis.warnings)
            
        if facility_analysis.critical_condition:
            self.safety_system.initiate_emergency_protocols(
                facility_analysis.critical_condition)
        
        # If online, report to regulatory service
        if self.mode == "ONLINE":
            try:
                self.service.report_facility_data(
                    radiation_data, temperature_data, 
                    pressure_data, facility_analysis)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return facility_analysis
```

## 100. Autonomous Laboratory System

```python
class AutonomousLaboratory:
    def __init__(self, lab_db_path, research_service=None, lab_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.lab_db = LocalLaboratoryDatabase(lab_db_path)
        self.local_controller = LocalLabController()
        self.sample_analyzers = SampleAnalyzerArray()
        self.robotic_manipulators = RoboticManipulatorArray()
        self.chemical_dispensers = ChemicalDispenserArray()
        self.imaging_system = LabImagingSystem()
        
        # Try once to connect to research service
        if research_service and lab_id:
            try:
                self.service = LabResearchService(research_service, lab_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest research parameters
                    self._sync_research_parameters()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def conduct_experiment(self, experiment_id, parameters):
        # Prepare the experiment
        setup = self.local_controller.prepare_experiment(experiment_id, parameters)
        
        # Set up equipment
        self.robotic_manipulators.configure(setup.manipulator_config)
        self.chemical_dispensers.configure(setup.dispenser_config)
        
        # Run the experiment
        experiment_results = self.local_controller.run_experiment(
            setup, self.robotic_manipulators, self.chemical_dispensers)
        
        # Analyze results
        sample_data = self.sample_analyzers.analyze_samples(experiment_results.samples)
        image_data = self.imaging_system.capture_images(experiment_results.imaging_targets)
        
        # Process results locally
        analysis_results = self.local_controller.analyze_experiment_results(
            experiment_id, sample_data, image_data)
        
        # Store results locally
        self.lab_db.store_experiment_results(
            experiment_id, parameters, experiment_results, 
            sample_data, image_data, analysis_results)
        
        # If online, report to research service
        if self.mode == "ONLINE":
            try:
                self.service.report_experiment_results(
                    experiment_id, parameters, experiment_results,
                    sample_data, image_data, analysis_results)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis_results
```

Each special purpose IoT system strictly implements MCP Zero's offline-first resilience pattern:
1. All systems start in offline mode by default
2. Only one connection attempt is made to remote services with a short timeout
3. Systems permanently revert to offline mode if connection fails or is lost later
4. Local processing ensures specialized functions continue without disruption regardless of network connectivity
5. Even in highly specialized applications like space habitats or nuclear facilities, systems remain fully operational without network connectivity
