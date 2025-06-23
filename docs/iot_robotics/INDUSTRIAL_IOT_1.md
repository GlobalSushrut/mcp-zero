# Industrial IoT and Manufacturing (16-20)

## 16. Factory Equipment Monitor

```python
class EquipmentMonitor:
    def __init__(self, equipment_db_path, monitoring_service=None, factory_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.equipment_db = LocalEquipmentDatabase(equipment_db_path)
        self.local_analyzer = LocalConditionMonitor()
        self.vibration_sensors = VibrationSensorArray()
        self.temperature_sensors = TemperatureSensorArray()
        self.alert_system = MaintenanceAlertSystem()
        
        # Try once to connect to monitoring service
        if monitoring_service and factory_id:
            try:
                self.service = EquipmentMonitoringService(monitoring_service, factory_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest equipment thresholds
                    self._update_thresholds()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_equipment(self):
        # Get sensor readings
        vibration_data = self.vibration_sensors.get_readings()
        temperature_data = self.temperature_sensors.get_readings()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_condition(
            vibration_data, temperature_data, self.equipment_db)
        
        # Process any alerts
        if analysis.requires_attention:
            self.alert_system.create_alert(analysis.equipment_id, 
                                          analysis.severity,
                                          analysis.recommended_action)
        
        # If online, report to monitoring service
        if self.mode == "ONLINE":
            try:
                self.service.report_condition(vibration_data, temperature_data)
                enhanced_analysis = self.service.get_predictive_analysis()
                if enhanced_analysis:
                    # Process any additional insights from the cloud
                    self._handle_enhanced_analysis(enhanced_analysis)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 17. Production Line Controller

```python
class ProductionLineController:
    def __init__(self, line_config_path, erp_service=None, line_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.line_config = ProductionLineConfig(line_config_path)
        self.local_scheduler = LocalProductionScheduler(self.line_config)
        self.production_sensors = ProductionSensorArray()
        self.machine_controllers = MachineControllerArray()
        self.local_order_queue = LocalOrderQueue()
        
        # Try once to connect to ERP service
        if erp_service and line_id:
            try:
                self.erp = ERPService(erp_service, line_id)
                if self.erp.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest production orders
                    self._sync_production_orders()
            except Exception:
                # No retry - stay with local scheduler
                self.erp = None
    
    def manage_production(self):
        # Get current production status
        status = self.production_sensors.get_status()
        
        # Always process orders from local queue
        production_plan = self.local_scheduler.create_plan(
            self.local_order_queue, status)
        
        # Apply the production plan
        self.machine_controllers.apply_plan(production_plan)
        
        # If online, report status and get updated orders
        if self.mode == "ONLINE":
            try:
                self.erp.report_production_status(status)
                new_orders = self.erp.get_new_orders()
                if new_orders:
                    self.local_order_queue.add_orders(new_orders)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.erp = None
        
        return production_plan
```

## 18. Quality Control System

```python
class QualityControlSystem:
    def __init__(self, standards_db_path, quality_service=None, factory_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.standards_db = QualityStandardsDatabase(standards_db_path)
        self.local_analyzer = LocalQualityAnalyzer(self.standards_db)
        self.vision_system = VisionInspectionSystem()
        self.measurement_sensors = PrecisionMeasurementArray()
        self.rejection_system = DefectRejectionSystem()
        
        # Try once to connect to quality service
        if quality_service and factory_id:
            try:
                self.service = QualityControlService(quality_service, factory_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest quality standards
                    self._update_standards()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def inspect_product(self, product_id):
        # Get inspection data
        visual_data = self.vision_system.capture_images()
        measurements = self.measurement_sensors.measure_product()
        
        # Always analyze locally first
        analysis = self.local_analyzer.analyze_quality(
            product_id, visual_data, measurements)
        
        # Take action based on analysis
        if not analysis.meets_standards:
            self.rejection_system.reject_product(product_id, analysis.defect_reasons)
        
        # If online, report inspection results
        if self.mode == "ONLINE":
            try:
                self.service.report_inspection(product_id, analysis, visual_data)
                model_updates = self.service.get_model_updates()
                if model_updates:
                    self.local_analyzer.update_model(model_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return analysis
```

## 19. Inventory Tracking System

```python
class InventoryTracker:
    def __init__(self, inventory_db_path, supply_chain_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.inventory_db = LocalInventoryDatabase(inventory_db_path)
        self.local_manager = LocalInventoryManager(self.inventory_db)
        self.rfid_readers = RFIDReaderArray()
        self.barcode_scanners = BarcodeScannerArray()
        self.indicator_system = InventoryIndicatorSystem()
        
        # Try once to connect to supply chain service
        if supply_chain_service and facility_id:
            try:
                self.service = SupplyChainService(supply_chain_service, facility_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync inventory data
                    self._sync_inventory()
            except Exception:
                # No retry - stay with local manager
                self.service = None
    
    def track_inventory_changes(self):
        # Get tracking data
        rfid_data = self.rfid_readers.scan_area()
        barcode_data = self.barcode_scanners.get_scans()
        
        # Always process locally first
        changes = self.local_manager.process_tracking_data(rfid_data, barcode_data)
        self.inventory_db.update(changes)
        
        # Update visual indicators
        levels = self.inventory_db.get_inventory_levels()
        self.indicator_system.update_indicators(levels)
        
        # If online, report inventory changes
        if self.mode == "ONLINE":
            try:
                self.service.report_inventory_changes(changes)
                orders = self.service.get_pending_orders()
                if orders:
                    self.local_manager.process_orders(orders)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return changes
```

## 20. Machine Utilization Optimizer

```python
class MachineUtilizationOptimizer:
    def __init__(self, machine_config_path, optimization_service=None, plant_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.machine_config = MachineConfigDatabase(machine_config_path)
        self.local_optimizer = LocalUtilizationOptimizer(self.machine_config)
        self.power_sensors = PowerSensorArray()
        self.utilization_sensors = UtilizationSensorArray()
        self.machine_controllers = MachineControllerArray()
        
        # Try once to connect to optimization service
        if optimization_service and plant_id:
            try:
                self.service = OptimizationService(optimization_service, plant_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local optimizer
                self.service = None
    
    def optimize_utilization(self):
        # Get current readings
        power_data = self.power_sensors.get_readings()
        utilization_data = self.utilization_sensors.get_readings()
        
        # Always optimize locally first
        schedule = self.local_optimizer.create_schedule(power_data, utilization_data)
        
        # Apply the schedule
        self.machine_controllers.apply_schedule(schedule)
        
        # If online, report data and get enhanced optimization
        if self.mode == "ONLINE":
            try:
                self.service.report_utilization_data(power_data, utilization_data)
                enhanced_schedule = self.service.get_enhanced_schedule()
                if enhanced_schedule:
                    # Apply enhanced schedule if available
                    self.machine_controllers.apply_schedule(enhanced_schedule)
                    schedule = enhanced_schedule
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return schedule
```

Each industrial IoT application implements MCP Zero's offline-first resilience pattern, ensuring critical functionality even without network connectivity. They all:
1. Start in offline mode by default
2. Make only one connection attempt to remote services
3. Fall back permanently to offline mode if connection fails
4. Rely on local processing for core operations
