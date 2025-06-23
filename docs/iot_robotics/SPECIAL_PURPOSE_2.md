# Special Purpose IoT (91-95)

## 91. Remote Research Station

```python
class RemoteResearchStation:
    def __init__(self, research_db_path, scientific_service=None, station_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.research_db = LocalResearchDatabase(research_db_path)
        self.local_controller = LocalResearchController()
        self.environmental_sensors = EnvironmentalSensorArray()
        self.specimen_analyzers = SpecimenAnalyzerArray()
        self.data_storage = LocalDataStorageSystem()
        
        # Try once to connect to scientific service
        if scientific_service and station_id:
            try:
                self.service = ScientificResearchService(scientific_service, station_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest research parameters
                    self._sync_research_parameters()
            except Exception:
                # No retry - stay with local controller
                self.service = None
    
    def collect_research_data(self):
        # Get sensor and analyzer readings
        environmental_data = self.environmental_sensors.get_readings()
        specimen_data = self.specimen_analyzers.get_readings()
        
        # Always process locally first
        research_analysis = self.local_controller.analyze_research_data(
            environmental_data, specimen_data)
        
        # Generate local research insights
        insights = self.local_controller.generate_insights(
            research_analysis, self.research_db)
        
        # Store data and insights locally
        self.data_storage.store_data(
            environmental_data, specimen_data, research_analysis, insights)
        self.research_db.update_with_findings(research_analysis, insights)
        
        # If online, report to scientific service
        if self.mode == "ONLINE":
            try:
                self.service.report_research_data(
                    environmental_data, specimen_data, research_analysis)
                
                research_feedback = self.service.get_research_feedback()
                if research_feedback:
                    self.research_db.incorporate_feedback(research_feedback)
                    enhanced_insights = self.local_controller.refine_insights(
                        insights, research_feedback)
                    self.data_storage.update_insights(enhanced_insights)
                    insights = enhanced_insights
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return research_analysis, insights
```

## 92. Supply Chain Verification System

```python
class SupplyChainVerifier:
    def __init__(self, supply_db_path, verification_service=None, company_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.supply_db = LocalSupplyChainDatabase(supply_db_path)
        self.local_verifier = LocalSupplyChainVerifier()
        self.rfid_readers = RFIDReaderArray()
        self.barcode_scanners = BarcodeScannerArray()
        self.blockchain_node = LocalBlockchainNode()
        
        # Try once to connect to verification service
        if verification_service and company_id:
            try:
                self.service = SupplyChainService(verification_service, company_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest verification parameters
                    self._sync_verification_parameters()
            except Exception:
                # No retry - stay with local verifier
                self.service = None
    
    def verify_product(self, product_id):
        # Get product data
        rfid_data = self.rfid_readers.scan_product(product_id)
        barcode_data = self.barcode_scanners.scan_product(product_id)
        
        # Always verify locally first
        verification_result = self.local_verifier.verify_product(
            product_id, rfid_data, barcode_data, self.supply_db)
        
        # Record verification in local blockchain
        self.blockchain_node.record_verification(
            product_id, verification_result)
        
        # Store verification data locally
        self.supply_db.store_verification(
            product_id, rfid_data, barcode_data, verification_result)
        
        # If online, report to verification service
        if self.mode == "ONLINE":
            try:
                self.service.report_verification(
                    product_id, rfid_data, barcode_data, verification_result)
                
                # Get enhanced verification from service
                enhanced_verification = self.service.get_enhanced_verification(product_id)
                if enhanced_verification:
                    verification_result = enhanced_verification
                    self.blockchain_node.update_verification(
                        product_id, enhanced_verification)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return verification_result
```

## 93. Remote Energy Production Monitor

```python
class RemoteEnergyMonitor:
    def __init__(self, energy_db_path, utility_service=None, site_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.energy_db = LocalEnergyDatabase(energy_db_path)
        self.local_analyzer = LocalEnergyAnalyzer()
        self.production_sensors = EnergyProductionSensorArray()
        self.environmental_sensors = EnvironmentalSensorArray()
        self.maintenance_system = MaintenanceManagementSystem()
        
        # Try once to connect to utility service
        if utility_service and site_id:
            try:
                self.service = EnergyProductionService(utility_service, site_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest energy parameters
                    self._sync_energy_parameters()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_energy_production(self):
        # Get sensor readings
        production_data = self.production_sensors.get_readings()
        environmental_data = self.environmental_sensors.get_readings()
        
        # Always analyze locally first
        production_analysis = self.local_analyzer.analyze_production(
            production_data, environmental_data)
        
        # Check for maintenance needs
        maintenance_needs = self.local_analyzer.identify_maintenance_needs(
            production_data, production_analysis)
        
        if maintenance_needs:
            self.maintenance_system.schedule_maintenance(maintenance_needs)
        
        # Calculate efficiency metrics
        efficiency_metrics = self.local_analyzer.calculate_efficiency_metrics(
            production_analysis)
        
        # Store data locally
        self.energy_db.store_production_data(
            production_data, environmental_data, 
            production_analysis, efficiency_metrics)
        
        # If online, report to utility service
        if self.mode == "ONLINE":
            try:
                self.service.report_production_data(
                    production_data, environmental_data, production_analysis)
                
                if maintenance_needs:
                    self.service.report_maintenance_needs(maintenance_needs)
                
                optimization_instructions = self.service.get_optimization_instructions()
                if optimization_instructions:
                    self.local_analyzer.apply_optimization_instructions(
                        optimization_instructions)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return production_analysis, efficiency_metrics
```

## 94. Autonomous Mine Safety System

```python
class MineSafetySystem:
    def __init__(self, mine_db_path, safety_service=None, mine_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.mine_db = LocalMineDatabase(mine_db_path)
        self.local_analyzer = LocalMineSafetyAnalyzer()
        self.gas_sensors = GasSensorArray()
        self.seismic_sensors = SeismicSensorArray()
        self.environmental_sensors = MineEnvironmentalSensors()
        self.alert_system = MineSafetyAlertSystem()
        
        # Try once to connect to safety service
        if safety_service and mine_id:
            try:
                self.service = MineSafetyService(safety_service, mine_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest safety parameters
                    self._sync_safety_parameters()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_mine_safety(self):
        # Get sensor readings
        gas_data = self.gas_sensors.get_readings()
        seismic_data = self.seismic_sensors.get_readings()
        environmental_data = self.environmental_sensors.get_readings()
        
        # Always analyze locally first
        safety_analysis = self.local_analyzer.analyze_safety_conditions(
            gas_data, seismic_data, environmental_data)
        
        # Store data locally
        self.mine_db.store_safety_data(
            gas_data, seismic_data, environmental_data, safety_analysis)
        
        # Handle any safety issues
        if safety_analysis.warnings:
            self.alert_system.issue_warnings(safety_analysis.warnings)
            
        if safety_analysis.critical_alerts:
            self.alert_system.trigger_evacuation(safety_analysis.critical_alerts)
        
        # If online, report to safety service
        if self.mode == "ONLINE":
            try:
                self.service.report_safety_data(
                    gas_data, seismic_data, environmental_data, safety_analysis)
                
                if safety_analysis.warnings or safety_analysis.critical_alerts:
                    response_protocols = self.service.get_response_protocols()
                    if response_protocols:
                        self.alert_system.update_protocols(response_protocols)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return safety_analysis
```

## 95. Archaeological Excavation Assistant

```python
class ArchaeologicalExcavationAssistant:
    def __init__(self, excavation_db_path, research_service=None, site_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.excavation_db = LocalExcavationDatabase(excavation_db_path)
        self.local_analyzer = LocalArchaeologicalAnalyzer()
        self.soil_sensors = SoilAnalysisSensorArray()
        self.imaging_system = MultiSpectralImagingSystem()
        self.artifact_scanner = ArtifactScanningSystem()
        
        # Try once to connect to research service
        if research_service and site_id:
            try:
                self.service = ArchaeologicalResearchService(research_service, site_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest archaeological models
                    self._sync_archaeological_models()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def analyze_excavation_area(self, area_id):
        # Get analysis data
        soil_data = self.soil_sensors.analyze_area(area_id)
        image_data = self.imaging_system.scan_area(area_id)
        
        # Always analyze locally first
        excavation_analysis = self.local_analyzer.analyze_area(
            soil_data, image_data, self.excavation_db)
        
        # Generate excavation recommendations
        recommendations = self.local_analyzer.generate_recommendations(
            excavation_analysis)
        
        # Store analysis locally
        self.excavation_db.store_area_analysis(
            area_id, soil_data, image_data, excavation_analysis, recommendations)
        
        # If artifacts are detected, analyze them
        artifact_analyses = []
        if excavation_analysis.potential_artifacts:
            for artifact in excavation_analysis.potential_artifacts:
                artifact_data = self.artifact_scanner.scan_artifact(artifact.id)
                artifact_analysis = self.local_analyzer.analyze_artifact(
                    artifact_data, self.excavation_db)
                
                self.excavation_db.store_artifact_analysis(
                    artifact.id, artifact_data, artifact_analysis)
                artifact_analyses.append(artifact_analysis)
        
        # If online, report to research service
        if self.mode == "ONLINE":
            try:
                self.service.report_excavation_data(
                    area_id, soil_data, image_data, excavation_analysis)
                
                if artifact_analyses:
                    self.service.report_artifact_analyses(artifact_analyses)
                
                research_insights = self.service.get_research_insights(area_id)
                if research_insights:
                    enhanced_recommendations = self.local_analyzer.incorporate_insights(
                        recommendations, research_insights)
                    self.excavation_db.update_recommendations(
                        area_id, enhanced_recommendations)
                    recommendations = enhanced_recommendations
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return excavation_analysis, recommendations, artifact_analyses
```

Each special purpose IoT system strictly implements MCP Zero's offline-first resilience pattern:
1. All systems start in offline mode by default
2. Only one connection attempt is made to remote services with a short timeout
3. Systems permanently revert to offline mode if connection fails or is lost later
4. Local processing ensures specialized functions continue without disruption regardless of network connectivity
5. Even in specialized applications like archaeological research or mine safety, systems remain fully operational without network connectivity
