# Industrial IoT and Manufacturing (26-30)

## 26. Robotic Process Automation Controller

```python
class RoboticProcessController:
    def __init__(self, robot_config_path, automation_service=None, cell_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.robot_config = RobotConfigDatabase(robot_config_path)
        self.local_planner = LocalTaskPlanner(self.robot_config)
        self.vision_system = VisionSystem()
        self.robot_arm = RobotArmController()
        self.safety_system = SafetyMonitor()
        
        # Try once to connect to automation service
        if automation_service and cell_id:
            try:
                self.service = AutomationService(automation_service, cell_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest task configurations
                    self._update_task_configurations()
            except Exception:
                # No retry - stay with local planner
                self.service = None
    
    def execute_process(self, task_id):
        # Get vision data
        workspace_data = self.vision_system.analyze_workspace()
        
        # Always plan locally first
        robot_plan = self.local_planner.create_plan(task_id, workspace_data)
        
        # Verify plan safety
        if self.safety_system.validate_plan(robot_plan, workspace_data):
            # Execute the validated plan
            self.robot_arm.execute_plan(robot_plan)
        
        # If online, report execution data
        if self.mode == "ONLINE":
            try:
                self.service.report_task_execution(task_id, robot_plan, workspace_data)
                optimizations = self.service.get_process_optimizations()
                if optimizations:
                    self.local_planner.update_optimizations(optimizations)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return robot_plan
```

## 27. Asset Tracking System

```python
class AssetTrackingSystem:
    def __init__(self, asset_db_path, tracking_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.asset_db = LocalAssetDatabase(asset_db_path)
        self.local_tracker = LocalAssetTracker()
        self.rfid_readers = RFIDReaderArray()
        self.location_beacons = LocationBeaconArray()
        
        # Try once to connect to tracking service
        if tracking_service and facility_id:
            try:
                self.service = AssetTrackingService(tracking_service, facility_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync asset database
                    self._sync_asset_database()
            except Exception:
                # No retry - stay with local tracker
                self.service = None
    
    def update_asset_locations(self):
        # Get tracking data
        rfid_data = self.rfid_readers.get_readings()
        beacon_data = self.location_beacons.get_readings()
        
        # Always process locally first
        location_updates = self.local_tracker.process_readings(rfid_data, beacon_data)
        self.asset_db.update_locations(location_updates)
        
        # If online, report location updates
        if self.mode == "ONLINE":
            try:
                self.service.report_location_updates(location_updates)
                asset_updates = self.service.get_asset_updates()
                if asset_updates:
                    self.asset_db.apply_updates(asset_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return location_updates
```

## 28. Manufacturing Execution System

```python
class ManufacturingExecutionSystem:
    def __init__(self, production_db_path, erp_service=None, plant_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.production_db = LocalProductionDatabase(production_db_path)
        self.local_scheduler = LocalProductionScheduler()
        self.machine_interfaces = MachineInterfaceArray()
        self.worker_interfaces = WorkerInterfaceArray()
        
        # Try once to connect to ERP service
        if erp_service and plant_id:
            try:
                self.erp = ERPService(erp_service, plant_id)
                if self.erp.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Sync production orders
                    self._sync_production_orders()
            except Exception:
                # No retry - stay with local scheduler
                self.erp = None
    
    def manage_production_workflow(self):
        # Get current status
        machine_status = self.machine_interfaces.get_status()
        worker_status = self.worker_interfaces.get_status()
        
        # Always schedule locally first
        work_orders = self.local_scheduler.create_work_orders(
            self.production_db, machine_status, worker_status)
        
        # Distribute work orders
        self.machine_interfaces.distribute_orders(work_orders.machine_orders)
        self.worker_interfaces.distribute_orders(work_orders.worker_orders)
        
        # If online, report status and get updated orders
        if self.mode == "ONLINE":
            try:
                self.erp.report_production_status(machine_status, worker_status)
                new_orders = self.erp.get_new_orders()
                if new_orders:
                    self.production_db.add_orders(new_orders)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.erp = None
        
        return work_orders
```

## 29. Factory Safety Monitor

```python
class FactorySafetyMonitor:
    def __init__(self, safety_standards_path, safety_service=None, facility_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.safety_standards = SafetyStandards(safety_standards_path)
        self.local_analyzer = LocalSafetyAnalyzer(self.safety_standards)
        self.safety_sensors = SafetySensorArray()
        self.alert_system = SafetyAlertSystem()
        self.emergency_controls = EmergencyControlSystem()
        
        # Try once to connect to safety service
        if safety_service and facility_id:
            try:
                self.service = SafetyMonitoringService(safety_service, facility_id)
                if self.service.authenticate(timeout=2):
                    self.mode = "ONLINE"
                    # Get latest safety standards
                    self._update_safety_standards()
            except Exception:
                # No retry - stay with local analyzer
                self.service = None
    
    def monitor_safety_conditions(self):
        # Get safety data
        sensor_data = self.safety_sensors.get_readings()
        
        # Always analyze locally first
        safety_status = self.local_analyzer.analyze_conditions(sensor_data)
        
        # Handle any safety issues
        if safety_status.has_violations:
            self.alert_system.create_alerts(safety_status.violations)
            
            if safety_status.requires_emergency_action:
                self.emergency_controls.activate(safety_status.recommended_actions)
        
        # If online, report safety status
        if self.mode == "ONLINE":
            try:
                self.service.report_safety_status(sensor_data, safety_status)
                standard_updates = self.service.get_standard_updates()
                if standard_updates:
                    self.safety_standards.apply_updates(standard_updates)
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return safety_status
```

## 30. Material Flow Optimizer

```python
class MaterialFlowOptimizer:
    def __init__(self, factory_layout_path, logistics_service=None, plant_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.factory_layout = FactoryLayout(factory_layout_path)
        self.local_optimizer = LocalMaterialFlowOptimizer(self.factory_layout)
        self.material_trackers = MaterialTrackingSystem()
        self.transport_system = MaterialTransportSystem()
        
        # Try once to connect to logistics service
        if logistics_service and plant_id:
            try:
                self.service = LogisticsService(logistics_service, plant_id)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Get latest logistics data
                    self._update_logistics_data()
            except Exception:
                # No retry - stay with local optimizer
                self.service = None
    
    def optimize_material_flow(self):
        # Get material tracking data
        tracking_data = self.material_trackers.get_status()
        
        # Always optimize locally first
        transport_plan = self.local_optimizer.create_plan(tracking_data)
        
        # Apply the transport plan
        self.transport_system.execute_plan(transport_plan)
        
        # If online, report data and get enhanced plan
        if self.mode == "ONLINE":
            try:
                self.service.report_material_status(tracking_data)
                external_constraints = self.service.get_external_constraints()
                if external_constraints:
                    # Create enhanced plan with external constraints
                    enhanced_plan = self.local_optimizer.create_plan_with_constraints(
                        tracking_data, external_constraints)
                    self.transport_system.execute_plan(enhanced_plan)
                    transport_plan = enhanced_plan
            except Exception:
                # On failure, permanently revert to offline
                self.mode = "OFFLINE"
                self.service = None
        
        return transport_plan
```

Each industrial IoT application demonstrates MCP Zero's offline-first resilience pattern:
1. Always starts in offline mode by default
2. Makes only one attempt to connect to remote services
3. If connection fails initially or drops later, permanently remains in offline mode
4. Maintains core functionality through local processing regardless of connectivity
5. When online, can take advantage of enhanced capabilities while maintaining offline resilience
