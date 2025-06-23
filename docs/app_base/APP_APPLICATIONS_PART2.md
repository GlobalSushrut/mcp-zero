# App-Based Applications Using MCP Zero (Part 2)

## Health and Wellness

### 16. Personal Health Tracker

```python
class HealthTracker:
    def __init__(self, local_db_path, sync_service_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_store = HealthDataStore(local_db_path)
        
        # Try once to connect to sync service
        if sync_service_url and api_key:
            try:
                self.sync = HealthDataSync(sync_service_url, api_key)
                if self.sync.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - remain in offline mode permanently
                self.sync = None
```

### 17. Meditation Guide

```python
class MeditationApp:
    def __init__(self, content_path, content_service_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_content = LocalMeditationContent(content_path)
        
        # Try once to connect to content service
        if content_service_url:
            try:
                self.content_service = RemoteMeditationContent(content_service_url)
                if self.content_service.connect(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local content
                self.content_service = None
```

### 18. Workout Planner

```python
class WorkoutPlanner:
    def __init__(self, local_storage_path, ai_coach_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_workouts = LocalWorkoutLibrary(local_storage_path)
        self.local_planner = BasicWorkoutPlanner()
        
        # Try once to connect to AI coach
        if ai_coach_url:
            try:
                self.ai_coach = RemoteAICoach(ai_coach_url)
                if self.ai_coach.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local planner
                self.ai_coach = None
```

### 19. Nutrition Tracker

```python
class NutritionTracker:
    def __init__(self, local_db_path, food_database_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalFoodDatabase(local_db_path)
        
        # Try once to connect to remote food database
        if food_database_url:
            try:
                self.remote_db = RemoteFoodDatabase(food_database_url)
                if self.remote_db.test_connection(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local database
                self.remote_db = None
```

### 20. Sleep Analysis Tool

```python
class SleepAnalyzer:
    def __init__(self, storage_path, analysis_service_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_storage = LocalSleepDataStore(storage_path)
        self.local_analyzer = BasicSleepAnalyzer()
        
        # Try once to connect to analysis service
        if analysis_service_url:
            try:
                self.remote_analyzer = AdvancedSleepAnalyzer(analysis_service_url)
                if self.remote_analyzer.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local analyzer
                self.remote_analyzer = None
```

## Finance and Business

### 21. Personal Finance Manager

```python
class FinanceManager:
    def __init__(self, local_db_path, bank_sync_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_store = LocalFinanceStorage(local_db_path)
        
        # Try once to connect to bank sync service
        if bank_sync_url:
            try:
                self.bank_sync = BankSyncService(bank_sync_url)
                if self.bank_sync.test_connection(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.bank_sync = None
```

### 22. Invoice Generator

```python
class InvoiceSystem:
    def __init__(self, storage_path, cloud_service_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_storage = LocalInvoiceStorage(storage_path)
        self.local_generator = BasicInvoiceGenerator()
        
        # Try once to connect to cloud service
        if cloud_service_url and api_key:
            try:
                self.cloud = CloudInvoiceService(cloud_service_url, api_key)
                if self.cloud.verify_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.cloud = None
```

### 23. Inventory Management

```python
class InventoryManager:
    def __init__(self, local_db_path, central_system_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalInventoryDatabase(local_db_path)
        
        # Try once to connect to central system
        if central_system_url:
            try:
                self.central = CentralInventorySystem(central_system_url)
                if self.central.test_connection(timeout=3):
                    self.mode = "ONLINE"
                    # Initial sync
                    self.central.sync_to_local(self.local_db)
            except Exception:
                # No retry - stay offline
                self.central = None
```

### 24. Business Analytics Dashboard

```python
class AnalyticsDashboard:
    def __init__(self, local_data_path, analytics_service_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_data = LocalAnalyticsData(local_data_path)
        self.local_processor = BasicAnalyticsProcessor()
        
        # Try once to connect to analytics service
        if analytics_service_url and api_key:
            try:
                self.service = AdvancedAnalyticsService(analytics_service_url, api_key)
                if self.service.verify_auth(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local processor
                self.service = None
```

### 25. Customer Relationship Management

```python
class CRMSystem:
    def __init__(self, local_db_path, cloud_crm_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalCRMDatabase(local_db_path)
        
        # Try once to connect to cloud CRM
        if cloud_crm_url and api_key:
            try:
                self.cloud_crm = CloudCRMService(cloud_crm_url, api_key)
                if self.cloud_crm.authenticate(timeout=3):
                    self.mode = "ONLINE"
                    # Initial sync
                    self.sync_data()
            except Exception:
                # No retry - stay offline
                self.cloud_crm = None
    
    def sync_data(self):
        if self.mode == "ONLINE":
            try:
                self.cloud_crm.sync_with_local(self.local_db)
            except Exception:
                # Permanent fallback on sync failure
                self.mode = "OFFLINE"
                self.cloud_crm = None
```

## Travel and Navigation

### 26. Offline-First Map Navigator

```python
class MapNavigator:
    def __init__(self, map_data_path, online_service_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.offline_maps = OfflineMapDatabase(map_data_path)
        self.local_routing = LocalRoutingEngine()
        
        # Try once to connect to online map service
        if online_service_url:
            try:
                self.online_maps = OnlineMapService(online_service_url)
                if self.online_maps.test_connection(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with offline maps
                self.online_maps = None
```

### 27. Travel Itinerary Planner

```python
class ItineraryPlanner:
    def __init__(self, local_db_path, travel_api_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalTravelDatabase(local_db_path)
        self.local_planner = BasicItineraryPlanner()
        
        # Try once to connect to travel API
        if travel_api_url and api_key:
            try:
                self.travel_api = TravelAPIClient(travel_api_url, api_key)
                if self.travel_api.verify_connection(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local planner
                self.travel_api = None
```

### 28. Local Guide and Points of Interest

```python
class LocalGuideApp:
    def __init__(self, poi_database_path, live_poi_service=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_pois = LocalPOIDatabase(poi_database_path)
        
        # Try once to connect to live POI service
        if live_poi_service:
            try:
                self.live_service = LivePOIService(live_poi_service)
                if self.live_service.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.live_service = None
```

### 29. Public Transportation Tracker

```python
class TransportTracker:
    def __init__(self, schedule_db_path, live_tracking_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.schedules = LocalTransportSchedules(schedule_db_path)
        
        # Try once to connect to live tracking
        if live_tracking_url:
            try:
                self.live_tracking = LiveTransportTracking(live_tracking_url)
                if self.live_tracking.connect(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with schedules only
                self.live_tracking = None
```

### 30. Accommodation Finder

```python
class AccommodationFinder:
    def __init__(self, local_listings_path, booking_service_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_listings = LocalAccommodationDatabase(local_listings_path)
        
        # Try once to connect to booking service
        if booking_service_url and api_key:
            try:
                self.booking_service = BookingServiceClient(booking_service_url, api_key)
                if self.booking_service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local listings
                self.booking_service = None
```

**Note:** This document continues with more app-based applications following MCP Zero's offline-first resilience pattern.
