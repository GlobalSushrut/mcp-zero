//! MCP-ZERO Hardware Manager Daemon
//!
//! Standalone service that monitors and enforces hardware constraints
//! for MCP-ZERO infrastructure.

use std::path::PathBuf;
use anyhow::Result;
use clap::{Parser, Subcommand};
use sysinfo::{SystemExt, ProcessExt};

// Import from the local library crate using the package name from Cargo.toml (mcp-hm -> mcp_hm)
use mcp_hm::{HardwareManager, HMConfig, ResourceStats, Alert, AlertLevel, AlertHandler, ConsoleAlertHandler, FileAlertHandler, ResourceType};

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Path to configuration file
    #[arg(short, long, value_name = "FILE")]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the hardware manager daemon
    Start {
        /// Run in foreground
        #[arg(short, long)]
        foreground: bool,
    },
    
    /// Check current resource usage
    Stats,
    
    /// Run a resource benchmark
    Benchmark {
        /// Duration in seconds
        #[arg(short, long, default_value = "10")]
        duration: u64,
    },
}

fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();
    
    // Parse command line arguments
    let cli = Cli::parse();
    
    // Load configuration
    let config = match &cli.config {
        Some(path) => HMConfig::from_file(path)?,
        None => HMConfig::from_env(),
    };
    
    // Validate config
    config.validate()?;
    
    // Print banner
    print_banner(&config);
    
    // Process command
    match cli.command.unwrap_or(Commands::Start { foreground: true }) {
        Commands::Start { foreground } => {
            if foreground {
                run_foreground(config)
            } else {
                run_daemon(config)
            }
        },
        Commands::Stats => print_stats(),
        Commands::Benchmark { duration } => run_benchmark(config, duration),
    }
}

/// Print application banner
fn print_banner(config: &HMConfig) {
    println!("╔═════════════════════════════════════════════╗");
    println!("║ MCP-ZERO v9 Hardware Manager                ║");
    println!("╠═════════════════════════════════════════════╣");
    println!("║ Constraints:                                ║");
    println!("║ - CPU: Max {:.1}%                           ║", config.max_cpu_percent);
    println!("║ - Memory: Max {} MB                        ║", config.max_memory_mb);
    println!("║ - Refresh: {} ms                          ║", config.refresh_interval_ms);
    println!("╚═════════════════════════════════════════════╝");
}

/// Run the hardware manager in foreground
fn run_foreground(config: HMConfig) -> Result<()> {
    tracing::info!("Starting MCP-ZERO Hardware Manager in foreground mode");
    
    // Create hardware manager
    let mut hm = HardwareManager::new(config);
    
    // Add console alert handler
    hm.add_alert_handler(Box::new(ConsoleAlertHandler));
    
    // Add file alert handler
    let log_path = PathBuf::from("mcp-hm.log");
    hm.add_alert_handler(Box::new(FileAlertHandler::new(log_path)));
    
    // Start monitoring
    hm.start_monitoring()?;
    
    tracing::info!("Hardware manager started, press Ctrl+C to stop");
    
    // Setup signal handler for graceful shutdown
    setup_signal_handler();
    
    // Block until signal received
    wait_for_signal();
    
    tracing::info!("Shutting down hardware manager");
    
    Ok(())
}

/// Run the hardware manager as a daemon
fn run_daemon(config: HMConfig) -> Result<()> {
    tracing::info!("Starting MCP-ZERO Hardware Manager in daemon mode");
    
    // Simple daemon implementation - in production would use a proper daemon framework
    std::thread::spawn(move || {
        // Create hardware manager
        let mut hm = HardwareManager::new(config);
        
        // Add file alert handler
        let log_path = PathBuf::from("mcp-hm.log");
        hm.add_alert_handler(Box::new(FileAlertHandler::new(log_path)));
        
        // Start monitoring
        if let Err(e) = hm.start_monitoring() {
            tracing::error!("Failed to start monitoring: {}", e);
            return;
        }
        
        // Setup signal handler
        setup_signal_handler();
        
        // Block until signal
        wait_for_signal();
    });
    
    println!("Hardware manager daemon started");
    
    Ok(())
}

/// Print current resource stats
fn print_stats() -> Result<()> {
    tracing::info!("Fetching current resource stats");
    
    // Create a system info collector
    let mut system = sysinfo::System::new_all();
    system.refresh_all();
    
    // Get own process ID
    let pid = std::process::id() as usize;
    
    // Get process info
    let process = system.process(sysinfo::Pid::from(pid))
        .ok_or_else(|| anyhow::anyhow!("Failed to get process info"))?;
    
    // Print stats
    println!("╔═════════════════════════════════════════════╗");
    println!("║ MCP-ZERO Hardware Stats                     ║");
    println!("╠═════════════════════════════════════════════╣");
    println!("║ CPU Usage:    {:.2}%                        ║", process.cpu_usage());
    println!("║ Memory Usage: {} MB                        ║", process.memory() / (1024 * 1024));
    println!("║ Virtual Mem:  {} MB                        ║", process.virtual_memory() / (1024 * 1024));
    println!("║ Runtime:      {}                   ║", format_duration(process.run_time()));
    println!("╚═════════════════════════════════════════════╝");
    
    Ok(())
}

/// Run a resource benchmark
fn run_benchmark(config: HMConfig, duration: u64) -> Result<()> {
    tracing::info!("Running resource benchmark for {} seconds", duration);
    
    println!("Starting benchmark with constraints:");
    println!("  - CPU: Max {:.1}%", config.max_cpu_percent);
    println!("  - Memory: Max {} MB", config.max_memory_mb);
    println!("  - Duration: {} seconds", duration);
    println!();
    
    // Start time
    let start = std::time::Instant::now();
    
    // Create system info collector
    let mut system = sysinfo::System::new_all();
    
    // Storage for samples
    let mut cpu_samples = Vec::new();
    let mut memory_samples = Vec::new();
    
    // Get own process ID
    let pid = std::process::id() as usize;
    
    // Sampling loop
    while start.elapsed() < std::time::Duration::from_secs(duration) {
        // Refresh system info
        system.refresh_all();
        
        // Get process info
        if let Some(process) = system.process(sysinfo::Pid::from(pid)) {
            let cpu = process.cpu_usage();
            let memory = process.memory() / (1024 * 1024); // Convert to MB
            
            cpu_samples.push(cpu);
            memory_samples.push(memory);
            
            print!("\rCPU: {:.2}%, Memory: {} MB", cpu, memory);
            std::io::Write::flush(&mut std::io::stdout()).ok();
        }
        
        // Sleep for a bit
        std::thread::sleep(std::time::Duration::from_millis(500));
    }
    
    println!("\n\nBenchmark complete!");
    
    // Calculate statistics
    if !cpu_samples.is_empty() && !memory_samples.is_empty() {
        let avg_cpu = cpu_samples.iter().sum::<f32>() / cpu_samples.len() as f32;
        let max_cpu = *cpu_samples.iter().max_by(|a, b| a.partial_cmp(b).unwrap()).unwrap();
        
        let avg_memory = memory_samples.iter().sum::<u64>() / memory_samples.len() as u64;
        let max_memory = *memory_samples.iter().max().unwrap();
        
        println!("\nResults:");
        println!("  CPU Usage:");
        println!("    - Average: {:.2}%", avg_cpu);
        println!("    - Maximum: {:.2}%", max_cpu);
        println!("    - Limit:   {:.2}%", config.max_cpu_percent);
        println!("    - Status:  {}", if max_cpu <= config.max_cpu_percent { "WITHIN LIMIT" } else { "EXCEEDED LIMIT" });
        
        println!("  Memory Usage:");
        println!("    - Average: {} MB", avg_memory);
        println!("    - Maximum: {} MB", max_memory);
        println!("    - Limit:   {} MB", config.max_memory_mb);
        println!("    - Status:  {}", if max_memory <= config.max_memory_mb as u64 { "WITHIN LIMIT" } else { "EXCEEDED LIMIT" });
    }
    
    Ok(())
}

/// Format duration in seconds to a human-readable string
fn format_duration(seconds: u64) -> String {
    let hours = seconds / 3600;
    let minutes = (seconds % 3600) / 60;
    let secs = seconds % 60;
    
    if hours > 0 {
        format!("{}h {}m {}s", hours, minutes, secs)
    } else if minutes > 0 {
        format!("{}m {}s", minutes, secs)
    } else {
        format!("{}s", secs)
    }
}

/// Setup signal handler for graceful shutdown
fn setup_signal_handler() {
    // In a real implementation, would use proper signal handling libraries
    // This is simplified for demonstration
    #[cfg(unix)]
    {
        use std::sync::atomic::{AtomicBool, Ordering};
        
        static SHUTDOWN: AtomicBool = AtomicBool::new(false);
        
        unsafe {
            libc::signal(libc::SIGINT, handle_signal as usize);
            libc::signal(libc::SIGTERM, handle_signal as usize);
        }
        
        extern "C" fn handle_signal(_: i32) {
            SHUTDOWN.store(true, Ordering::SeqCst);
        }
    }
}

/// Wait for shutdown signal
fn wait_for_signal() {
    #[cfg(unix)]
    {
        use std::sync::atomic::{AtomicBool, Ordering};
        
        static SHUTDOWN: AtomicBool = AtomicBool::new(false);
        
        while !SHUTDOWN.load(Ordering::SeqCst) {
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
    }
    
    #[cfg(not(unix))]
    {
        // Just sleep for demo purposes
        std::thread::sleep(std::time::Duration::from_secs(3600));
    }
}
