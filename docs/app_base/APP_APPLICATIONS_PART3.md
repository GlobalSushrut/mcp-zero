# App-Based Applications Using MCP Zero (Part 3)

## Entertainment and Media

### 31. Offline-First Media Player

```python
class MediaPlayer:
    def __init__(self, local_library_path, streaming_service_url=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_library = LocalMediaLibrary(local_library_path)
        
        # Try once to connect to streaming service
        if streaming_service_url and api_key:
            try:
                self.streaming = StreamingService(streaming_service_url, api_key)
                if self.streaming.authenticate(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local library
                self.streaming = None
```

### 32. Reading App with Local Library

```python
class ReadingApp:
    def __init__(self, library_path, store_url=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_library = LocalBookLibrary(library_path)
        
        # Try once to connect to bookstore
        if store_url:
            try:
                self.store = OnlineBookstore(store_url)
                if self.store.test_connection(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local library
                self.store = None
```

### 33. Game Platform with Local Play

```python
class GamePlatform:
    def __init__(self, games_directory, multiplayer_service=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_games = LocalGameLibrary(games_directory)
        self.local_play = LocalPlayService()
        
        # Try once to connect to multiplayer service
        if multiplayer_service:
            try:
                self.multiplayer = MultiplayerService(multiplayer_service)
                if self.multiplayer.connect(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local play
                self.multiplayer = None
```

### 34. Podcast Management

```python
class PodcastManager:
    def __init__(self, download_dir, directory_service=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_podcasts = LocalPodcastLibrary(download_dir)
        
        # Try once to connect to podcast directory
        if directory_service:
            try:
                self.directory = PodcastDirectory(directory_service)
                if self.directory.connect(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.directory = None
```

### 35. Social Media Viewer with Local Cache

```python
class SocialViewer:
    def __init__(self, cache_dir, social_api_url=None, auth_token=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.cache = SocialFeedCache(cache_dir)
        
        # Try once to connect to social API
        if social_api_url and auth_token:
            try:
                self.api = SocialAPIClient(social_api_url, auth_token)
                if self.api.verify_auth(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with cache
                self.api = None
```

## Communication and Messaging

### 36. Offline-First Email Client

```python
class EmailClient:
    def __init__(self, local_mail_path, mail_server=None, credentials=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_mail = LocalMailstore(local_mail_path)
        
        # Try once to connect to mail server
        if mail_server and credentials:
            try:
                self.server = MailServer(mail_server, credentials)
                if self.server.connect(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.server = None
```

### 37. Chat Application with Message Queue

```python
class ChatApp:
    def __init__(self, local_storage_path, chat_server=None, user_token=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_storage = LocalChatStorage(local_storage_path)
        self.message_queue = OutgoingMessageQueue()
        
        # Try once to connect to chat server
        if chat_server and user_token:
            try:
                self.server = ChatServer(chat_server, user_token)
                if self.server.authenticate(timeout=2):
                    self.mode = "ONLINE"
                    # Try to send queued messages
                    self._send_queued_messages()
            except Exception:
                # No retry - stay offline
                self.server = None
```

### 38. Video Conferencing Client

```python
class VideoConferencing:
    def __init__(self, local_cache_path, conferencing_service=None, credentials=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_cache = ConferenceCache(local_cache_path)
        
        # Try once to connect to conferencing service
        if conferencing_service and credentials:
            try:
                self.service = ConferencingService(conferencing_service, credentials)
                if self.service.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.service = None
```

### 39. Group Coordination Tool

```python
class GroupCoordinator:
    def __init__(self, local_data_path, coordination_server=None, group_id=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_data = LocalGroupData(local_data_path)
        
        # Try once to connect to coordination server
        if coordination_server and group_id:
            try:
                self.server = CoordinationServer(coordination_server, group_id)
                if self.server.connect(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.server = None
```

### 40. Secure Document Sharing

```python
class SecureDocumentSharing:
    def __init__(self, local_vault_path, sharing_service=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_vault = DocumentVault(local_vault_path)
        
        # Try once to connect to sharing service
        if sharing_service and api_key:
            try:
                self.sharing = DocumentSharingService(sharing_service, api_key)
                if self.sharing.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.sharing = None
```

## Utility Applications

### 41. Language Translation Tool

```python
class TranslationTool:
    def __init__(self, local_model_path, translation_api=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_translator = LocalTranslator(local_model_path)
        
        # Try once to connect to translation API
        if translation_api and api_key:
            try:
                self.api_translator = APITranslator(translation_api, api_key)
                if self.api_translator.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local translator
                self.api_translator = None
```

### 42. Weather Forecast App

```python
class WeatherApp:
    def __init__(self, cached_data_path, weather_api=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.cached_data = CachedWeatherData(cached_data_path)
        self.local_forecaster = LocalWeatherForecaster()
        
        # Try once to connect to weather API
        if weather_api and api_key:
            try:
                self.api = WeatherAPIClient(weather_api, api_key)
                if self.api.test_connection(timeout=2):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with cached data
                self.api = None
```

### 43. Unit Conversion Tool

```python
class UnitConverter:
    def __init__(self, local_db_path, conversion_service=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_db = LocalConversionDatabase(local_db_path)
        
        # Try once to connect to conversion service for latest rates
        if conversion_service:
            try:
                self.service = ConversionService(conversion_service)
                if self.service.connect(timeout=2):
                    self.mode = "ONLINE"
                    # Update local database
                    self.local_db.update_from(self.service)
            except Exception:
                # No retry - stay with local database
                self.service = None
```

### 44. Password Manager

```python
class PasswordManager:
    def __init__(self, vault_path, sync_service=None, master_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.vault = PasswordVault(vault_path)
        
        # Try once to connect to sync service
        if sync_service and master_key:
            try:
                self.sync = VaultSyncService(sync_service, master_key)
                if self.sync.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay offline
                self.sync = None
```

### 45. File Backup Tool

```python
class BackupTool:
    def __init__(self, local_backup_path, cloud_service=None, api_key=None):
        self.mode = "OFFLINE"  # Start offline by default
        self.local_backup = LocalBackupStorage(local_backup_path)
        
        # Try once to connect to cloud service
        if cloud_service and api_key:
            try:
                self.cloud = CloudBackupService(cloud_service, api_key)
                if self.cloud.authenticate(timeout=3):
                    self.mode = "ONLINE"
            except Exception:
                # No retry - stay with local backup
                self.cloud = None
```

**Note:** This document continues with more app-based applications following MCP Zero's offline-first resilience pattern.
