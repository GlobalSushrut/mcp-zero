//! Alert system for MCP-ZERO Hardware Manager
//!
//! Provides alerting mechanisms when resource constraints are violated
//! or approaching thresholds.

use std::fmt;
use serde::{Serialize, Deserialize};
use crate::resource::ResourceType;

/// Alert level
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AlertLevel {
    /// Informational alert
    Info,
    /// Warning alert
    Warning,
    /// Critical alert
    Critical,
    /// Fatal alert (requires immediate action)
    Fatal,
}

impl fmt::Display for AlertLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AlertLevel::Info => write!(f, "INFO"),
            AlertLevel::Warning => write!(f, "WARNING"),
            AlertLevel::Critical => write!(f, "CRITICAL"),
            AlertLevel::Fatal => write!(f, "FATAL"),
        }
    }
}

/// Alert message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    /// Alert level
    pub level: AlertLevel,
    
    /// Resource type triggering the alert
    pub resource_type: ResourceType,
    
    /// Alert message
    pub message: String,
    
    /// Current value
    pub current_value: f64,
    
    /// Threshold value
    pub threshold_value: f64,
    
    /// Timestamp
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl Alert {
    /// Create a new alert
    pub fn new(
        level: AlertLevel,
        resource_type: ResourceType,
        message: &str,
        current_value: f64,
        threshold_value: f64,
    ) -> Self {
        Self {
            level,
            resource_type,
            message: message.to_string(),
            current_value,
            threshold_value,
            timestamp: chrono::Utc::now(),
        }
    }
    
    /// Format alert as string
    pub fn format(&self) -> String {
        format!(
            "[{}] {} - {}: current={:.2}, threshold={:.2}",
            self.level,
            self.timestamp.to_rfc3339(),
            self.message,
            self.current_value,
            self.threshold_value
        )
    }
}

/// Alert handler trait
pub trait AlertHandler: Send + Sync {
    /// Handle an alert
    fn handle(&self, alert: &Alert);
}

/// Console alert handler
pub struct ConsoleAlertHandler;

impl AlertHandler for ConsoleAlertHandler {
    fn handle(&self, alert: &Alert) {
        match alert.level {
            AlertLevel::Info => tracing::info!("{}", alert.format()),
            AlertLevel::Warning => tracing::warn!("{}", alert.format()),
            AlertLevel::Critical => tracing::error!("{}", alert.format()),
            AlertLevel::Fatal => tracing::error!("{}", alert.format()),
        }
    }
}

/// File alert handler
pub struct FileAlertHandler {
    /// Output file path
    path: std::path::PathBuf,
}

impl FileAlertHandler {
    /// Create a new file alert handler
    pub fn new<P: AsRef<std::path::Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }
}

impl AlertHandler for FileAlertHandler {
    fn handle(&self, alert: &Alert) {
        // Format alert
        let formatted = format!(
            "{} [{}] {}\n",
            alert.timestamp.to_rfc3339(),
            alert.level,
            alert.message
        );
        
        // Append to file
        if let Err(e) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .and_then(|mut file| std::io::Write::write_all(&mut file, formatted.as_bytes()))
        {
            tracing::error!("Failed to write alert to file: {}", e);
        }
    }
}

/// Alert manager
pub struct AlertManager {
    /// Alert handlers
    handlers: Vec<Box<dyn AlertHandler>>,
    
    /// Minimum level to trigger alerts
    min_level: AlertLevel,
}

impl AlertManager {
    /// Create a new alert manager
    pub fn new(min_level: AlertLevel) -> Self {
        Self {
            handlers: Vec::new(),
            min_level,
        }
    }
    
    /// Add an alert handler
    pub fn add_handler(&mut self, handler: Box<dyn AlertHandler>) {
        self.handlers.push(handler);
    }
    
    /// Emit an alert
    pub fn emit(&self, alert: Alert) {
        // Check if alert level meets minimum threshold
        if alert.level as u8 >= self.min_level as u8 {
            // Send to all handlers
            for handler in &self.handlers {
                handler.handle(&alert);
            }
        }
    }
    
    /// Create and emit an alert with the given parameters
    pub fn send(
        &self,
        level: AlertLevel,
        resource_type: ResourceType,
        message: &str,
        current_value: f64,
        threshold_value: f64,
    ) {
        let alert = Alert::new(level, resource_type, message, current_value, threshold_value);
        self.emit(alert);
    }
}
