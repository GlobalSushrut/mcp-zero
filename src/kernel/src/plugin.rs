//! Plugin system for MCP-ZERO kernel
//!
//! Implements a WASM-based plugin system with capability-based security,
//! allowing for modular extension of the infrastructure.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use anyhow::{Result, Context, anyhow};
use serde::{Serialize, Deserialize};
use wasmtime::{Engine, Module, Store, Linker, Caller, Func};

use crate::agent::AgentId;

/// Plugin ID type
pub type PluginId = String;

/// Plugin capability configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginCapabilities {
    /// Whether the plugin can access agent state
    #[serde(default)]
    pub state_access: bool,
    
    /// Whether the plugin can call other plugins
    #[serde(default)]
    pub plugin_call: bool,
    
    /// Whether the plugin can access external resources
    #[serde(default)]
    pub external_access: bool,
    
    /// CPU usage limit in percentage
    #[serde(default = "default_cpu_limit")]
    pub cpu_limit: f32,
    
    /// Memory usage limit in MB
    #[serde(default = "default_memory_limit")]
    pub memory_limit: u32,
    
    /// Additional capabilities
    #[serde(default)]
    pub additional: HashMap<String, serde_json::Value>,
}

fn default_cpu_limit() -> f32 {
    5.0 // Default 5% CPU limit per plugin
}

fn default_memory_limit() -> u32 {
    50 // Default 50MB memory limit per plugin
}

impl Default for PluginCapabilities {
    fn default() -> Self {
        Self {
            state_access: false,
            plugin_call: false,
            external_access: false,
            cpu_limit: default_cpu_limit(),
            memory_limit: default_memory_limit(),
            additional: HashMap::new(),
        }
    }
}

/// Plugin metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginMetadata {
    /// Plugin name
    pub name: String,
    
    /// Plugin version
    pub version: String,
    
    /// Plugin author
    pub author: String,
    
    /// Plugin description
    pub description: String,
    
    /// Plugin hash for verification
    pub hash: Option<String>,
    
    /// Additional metadata
    #[serde(default)]
    pub additional: HashMap<String, String>,
}

impl Default for PluginMetadata {
    fn default() -> Self {
        Self {
            name: String::new(),
            version: "0.1.0".to_string(),
            author: String::new(),
            description: String::new(),
            hash: None,
            additional: HashMap::new(),
        }
    }
}

/// Plugin implementation
// Wrapper for Module that implements Debug
pub struct DebugModule(Arc<Module>);

impl std::fmt::Debug for DebugModule {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("WasmModule").finish()
    }
}

impl From<Arc<Module>> for DebugModule {
    fn from(module: Arc<Module>) -> Self {
        DebugModule(module)
    }
}

impl AsRef<Module> for DebugModule {
    fn as_ref(&self) -> &Module {
        self.0.as_ref()
    }
}

#[derive(Debug)]
pub struct Plugin {
    /// Unique plugin identifier
    id: PluginId,
    
    /// Capabilities & permissions
    capabilities: PluginCapabilities,
    
    /// Plugin metadata
    metadata: PluginMetadata,
    
    /// WASM module
    module: Option<DebugModule>,
    
    /// Whether the plugin is loaded
    loaded: bool,
}

impl Plugin {
    /// Create a new Plugin instance with full details
    pub fn new(
        id: PluginId,
        capabilities: PluginCapabilities,
        metadata: PluginMetadata,
        module: Module,
    ) -> Self {
        let debug_module = DebugModule::from(Arc::new(module));
        let plugin = Plugin {
            id,
            capabilities,
            metadata,
            module: Some(debug_module),
            loaded: true,
        };
        plugin
    }
    
    /// Create a placeholder Plugin instance (not fully loaded)
    pub fn placeholder(id: &PluginId) -> Self {
        Self {
            id: id.clone(),
            capabilities: PluginCapabilities::default(),
            metadata: PluginMetadata::default(),
            module: None,
            loaded: false,
        }
    }
    
    /// Get plugin ID
    pub fn id(&self) -> &PluginId {
        &self.id
    }
    
    /// Get plugin capabilities
    pub fn capabilities(&self) -> &PluginCapabilities {
        &self.capabilities
    }
    
    /// Get plugin metadata
    pub fn metadata(&self) -> &PluginMetadata {
        &self.metadata
    }
    
    /// Check if the plugin is loaded
    pub fn is_loaded(&self) -> bool {
        self.loaded
    }
    
    /// Execute the plugin with an intent
    pub fn execute(
        &self,
        intent: &str,
        agent_id: &AgentId,
        state: &HashMap<String, serde_json::Value>,
    ) -> Result<serde_json::Value> {
        // If the plugin is not loaded, return an error
        if !self.loaded {
            return Err(anyhow!("Plugin {} is not loaded", self.id));
        }
        
        // Ensure we have a module
        let debug_module = match &self.module {
            Some(m) => m,
            None => return Err(anyhow!("Plugin {} has no module loaded", self.id)),
        };
        // Access the underlying Module reference
        let module_ref = debug_module.as_ref();
        
        // Create a new store
        let engine = Engine::default();
        let mut store = Store::new(&engine, PluginState {
            agent_id: agent_id.clone(),
            intent: intent.to_string(),
            state: state.clone(),
            result: None,
        });
        
        // Create a linker with the appropriate host functions
        let mut linker = Linker::new(&engine);
        
        // Define host functions that the plugin can call
        Self::define_host_functions(&mut linker)?;
        
        // Instantiate the module
        let instance = linker.instantiate(&mut store, module_ref)?;
        
        // Get the execute function
        let execute = instance.get_func(&mut store, "execute")
            .ok_or_else(|| anyhow!("Plugin {} does not export 'execute' function", self.id))?;
        
        // Execute the function
        execute.call(&mut store, &[], &mut [])?;
        
        // Get the result
        let result = store.data().result.clone()
            .unwrap_or_else(|| serde_json::json!({"status": "executed", "result": null}));
        
        Ok(result)
    }
    
    /// Define host functions for the WASM module
    fn define_host_functions(linker: &mut Linker<PluginState>) -> Result<()> {
        // Function to set the execution result
        linker.func_wrap("host", "set_result", |mut caller: Caller<'_, PluginState>, ptr: u32, len: u32| {
            let memory = match caller.get_export("memory") {
                Some(wasmtime::Extern::Memory(mem)) => mem,
                _ => return Err(anyhow!("Failed to get memory export")),
            };
            
            // Read the result data from the module's memory
            let data = match memory.data(&caller).get(ptr as usize..(ptr + len) as usize) {
                Some(data) => data,
                None => return Err(anyhow!("Invalid memory range")),
            };
            
            // Convert to JSON
            let result: serde_json::Value = match serde_json::from_slice(data) {
                Ok(v) => v,
                Err(e) => return Err(anyhow!("Failed to parse result as JSON: {}", e)),
            };
            
            // Set the result
            caller.data_mut().result = Some(result);
            
            Ok(())
        })?;
        
        // Function to get the intent
        linker.func_wrap("host", "get_intent", |mut caller: Caller<'_, PluginState>, ptr: u32| -> Result<u32, anyhow::Error> {
            let memory = match caller.get_export("memory") {
                Some(wasmtime::Extern::Memory(mem)) => mem,
                _ => return Err(anyhow!("Failed to get memory export")),
            };
            
            // Create a copy of the intent data to avoid the borrow conflict
            let intent_data = caller.data().intent.clone();
            let intent = intent_data.as_bytes();
            let len = intent.len();
            
            // Write the intent to the module's memory
            let mem_slice = match memory.data_mut(&mut caller).get_mut(ptr as usize..(ptr + len as u32) as usize) {
                Some(slice) => slice,
                None => return Err(anyhow!("Invalid memory range")),
            };
            mem_slice.copy_from_slice(intent);
            
            Ok(len as u32)
        })?;
        
        // Add more host functions as needed
        
        Ok(())
    }
}

/// Plugin Manager for loading and managing plugins
pub struct PluginManager {
    /// Directory for plugin files
    plugin_dir: PathBuf,
    
    /// Loaded plugins
    plugins: Arc<RwLock<HashMap<PluginId, Arc<Plugin>>>>,
    
    /// WASM engine
    engine: Engine,
}

impl PluginManager {
    /// Create a new PluginManager
    pub fn new<P: AsRef<Path>>(plugin_dir: P) -> Self {
        Self {
            plugin_dir: plugin_dir.as_ref().to_path_buf(),
            plugins: Arc::new(RwLock::new(HashMap::new())),
            engine: Engine::default(),
        }
    }
    
    /// Load a plugin by ID
    pub fn load_plugin(&self, plugin_id: &PluginId) -> Result<Arc<Plugin>> {
        // Check if plugin is already loaded
        {
            let plugins = self.plugins.read().map_err(|_| anyhow!("Failed to acquire read lock"))?;
            if let Some(plugin) = plugins.get(plugin_id) {
                return Ok(plugin.clone());
            }
        }
        
        // Construct plugin file path
        let plugin_path = self.plugin_dir.join(format!("{}.wasm", plugin_id));
        let cap_path = self.plugin_dir.join(format!("{}.cap.yaml", plugin_id));
        
        // Verify the plugin exists
        if !plugin_path.exists() {
            return Err(anyhow!("Plugin file not found: {}", plugin_path.display()));
        }
        
        // Load capabilities
        let capabilities = if cap_path.exists() {
            match std::fs::read_to_string(&cap_path) {
                Ok(content) => serde_yaml::from_str(&content)
                    .with_context(|| format!("Failed to parse capabilities file: {}", cap_path.display()))?,
                Err(e) => return Err(anyhow!("Failed to read capabilities file: {}", e)),
            }
        } else {
            PluginCapabilities::default()
        };
        
        // Load and compile the WASM module
        let module = Module::from_file(&self.engine, &plugin_path)
            .with_context(|| format!("Failed to load WASM module: {}", plugin_path.display()))?;
        
        // Extract metadata from the module (placeholder for now)
        let metadata = PluginMetadata {
            name: plugin_id.clone(),
            version: "1.0.0".to_string(),
            author: "Unknown".to_string(),
            description: "No description available".to_string(),
            hash: None,
            additional: HashMap::new(),
        };
        
        // Create plugin instance
        let plugin = Arc::new(Plugin::new(
            plugin_id.clone(),
            capabilities,
            metadata,
            module,
        ));
        
        // Store plugin
        let mut plugins = self.plugins.write().map_err(|_| anyhow!("Failed to acquire write lock"))?;
        plugins.insert(plugin_id.clone(), plugin.clone());
        
        Ok(plugin)
    }
}

/// Plugin state for WASM execution
#[derive(Debug)]
struct PluginState {
    /// Agent ID
    agent_id: AgentId,
    
    /// Intent being executed
    intent: String,
    
    /// Agent state
    state: HashMap<String, serde_json::Value>,
    
    /// Execution result
    result: Option<serde_json::Value>,
}
