#!/usr/bin/env python3
"""
Dev Agent: Voice-Interactive Code Assistant using MCP-ZERO
Shows off MCP-ZERO's traceability and code generation capabilities.
"""
import os
import sys
import time
import json
import tempfile
import subprocess
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP-ZERO imports
from pare_protocol.chain_protocol import PAREChainProtocol as PAREProtocol
from pare_protocol.intent_weight_bias import IntentWeightBias

class CodeProject:
    """Represents a code project managed by the Dev Agent"""
    
    def __init__(self, project_name, project_dir=None):
        self.name = project_name
        self.project_dir = project_dir or os.path.join(tempfile.gettempdir(), project_name)
        self.files = {}  # filename -> content
        
        # Create project directory if it doesn't exist
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)
            print(f"Created project directory: {self.project_dir}")
            
    def create_file(self, filename, content=""):
        """Create or overwrite a file in the project"""
        filepath = os.path.join(self.project_dir, filename)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write content to file
        with open(filepath, 'w') as f:
            f.write(content)
            
        # Store in memory
        self.files[filename] = content
        return filepath
        
    def read_file(self, filename):
        """Read file content from the project"""
        filepath = os.path.join(self.project_dir, filename)
        
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Update in-memory cache
        self.files[filename] = content
        return content
        
    def list_files(self):
        """List all files in the project"""
        files = []
        for root, _, filenames in os.walk(self.project_dir):
            rel_root = os.path.relpath(root, self.project_dir)
            for filename in filenames:
                if rel_root == ".":
                    files.append(filename)
                else:
                    files.append(os.path.join(rel_root, filename))
        return files
        
    def run_command(self, command):
        """Run a shell command in the project directory"""
        try:
            result = subprocess.run(
                command, 
                cwd=self.project_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10  # Limit execution time
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 10 seconds",
                "code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "code": -1
            }

class DevAgent:
    """Voice-interactive code assistant using MCP-ZERO"""
    
    def __init__(self):
        # Initialize MCP-ZERO components
        # Create a db path for this demo
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "dev_agent.db")
        self.protocol = PAREProtocol(db_path=db_path, rpc_url="http://localhost:50051")
        self.agent_id = "dev-agent"
        self.intent_bias = IntentWeightBias(dimensions=(6, 6))
        
        # Track active projects
        self.active_project = None
        self.projects = {}
        
        # Template snippets for code generation
        self.templates = {
            "flask_app": {
                "app.py": """from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Flask App is running!"

if __name__ == '__main__':
    app.run(debug=True)
""",
                "requirements.txt": """flask==2.0.1
"""
            },
            "flask_login": {
                "login.py": """from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory user store (would use database in production)
users = {}

# JWT configuration
JWT_SECRET = 'your-secret-key'  # In production, use a secure key
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    if username in users:
        return jsonify({"error": "Username already exists"}), 400
        
    users[username] = {
        'username': username,
        'password': generate_password_hash(password)
    }
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    if username not in users:
        return jsonify({"error": "Invalid credentials"}), 401
        
    user = users[username]
    
    if not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    # Generate JWT token
    payload = {
        'user_id': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    
    return jsonify({
        "token": token,
        "message": "Login successful"
    })

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({"error": "Token is missing"}), 401
        
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except (jwt.InvalidTokenError, KeyError):
        return jsonify({"error": "Invalid token"}), 401
        
    return jsonify({
        "message": f"Hello {username}, this is a protected endpoint!"
    })

if __name__ == '__main__':
    app.run(debug=True)
""",
                "requirements.txt": """flask==2.0.1
werkzeug==2.0.1
pyjwt==2.1.0
"""
            }
        }
        
    def process_command(self, command: str) -> Dict[str, Any]:
        """Process a natural language coding command"""
        # Create training block
        trace_id = self.protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="dev_command",
            metadata={"timestamp": time.time()}
        )
        
        # Record command in training block
        self.protocol.add_training_data(
            block_id=trace_id,
            data_content=json.dumps({"command": command}),
            data_type="user_command",
            metadata={"agent_id": self.agent_id}
        )
        
        # Process command
        response = {"success": False, "message": "Command not recognized"}
        
        # Create project
        if command.lower().startswith(("create", "new", "make")) and "project" in command.lower():
            project_name = self._extract_project_name(command)
            response = self._create_project(project_name)
            
        # Create file
        elif command.lower().startswith(("create", "add", "new")) and "file" in command.lower():
            filename = self._extract_filename(command)
            response = self._create_file(filename)
            
        # Build specific component  
        elif "build" in command.lower() or "create" in command.lower():
            response = self._build_component(command)
            
        # Run code
        elif command.lower().startswith(("run", "execute", "test")):
            response = self._run_code(command)
            
        # List files
        elif "list" in command.lower() and "files" in command.lower():
            response = self._list_files()
            
        # Show file content
        elif "show" in command.lower() and ("file" in command.lower() or "code" in command.lower()):
            filename = self._extract_filename(command)
            response = self._show_file(filename)
        
        # Record result in training block
        self.protocol.add_llm_call(
            block_id=trace_id,
            prompt=command,
            result=json.dumps(response),
            metadata={"agent_id": self.agent_id, "model": "dev-agent-v1"}
        )
        
        # Training block is automatically managed (no need to close)
        
        return response
    
    def _extract_project_name(self, command):
        """Extract project name from command"""
        # Simple extraction - in production would use NLP
        words = command.split()
        for i, word in enumerate(words):
            if word.lower() in ["project", "app", "application"] and i > 0:
                return words[i-1]
        
        # Default name
        return "my_project"
    
    def _extract_filename(self, command):
        """Extract filename from command"""
        # Simple extraction - in production would use NLP
        words = command.split()
        for i, word in enumerate(words):
            if word.lower() in ["file", "module"] and i+1 < len(words):
                return words[i+1]
        
        # Check for common extensions
        for word in words:
            if "." in word and word.split(".")[-1] in ["py", "js", "html", "css", "txt"]:
                return word
        
        # Default name
        return "main.py"
    
    def _create_project(self, project_name):
        """Create a new project"""
        if project_name in self.projects:
            return {
                "success": False,
                "message": f"Project '{project_name}' already exists"
            }
        
        # Create project
        self.active_project = CodeProject(project_name)
        self.projects[project_name] = self.active_project
        
        return {
            "success": True,
            "message": f"Created project '{project_name}' at {self.active_project.project_dir}",
            "project_dir": self.active_project.project_dir
        }
    
    def _create_file(self, filename):
        """Create a new file in the active project"""
        if not self.active_project:
            return {
                "success": False,
                "message": "No active project. Create a project first."
            }
        
        filepath = self.active_project.create_file(filename, "# New file created by Dev Agent\n")
        
        return {
            "success": True,
            "message": f"Created file '{filename}' in project '{self.active_project.name}'",
            "filepath": filepath
        }
    
    def _build_component(self, command):
        """Build a component based on command"""
        if not self.active_project:
            return {
                "success": False,
                "message": "No active project. Create a project first."
            }
        
        # Flask Login Form
        if "login" in command.lower() and ("flask" in command.lower() or "web" in command.lower()):
            files_created = []
            
            # Create login system from template
            for filename, content in self.templates["flask_login"].items():
                filepath = self.active_project.create_file(filename, content)
                files_created.append(filename)
            
            return {
                "success": True,
                "message": f"Built Flask login system with JWT authentication in {self.active_project.name}",
                "files_created": files_created
            }
        
        # Basic Flask app
        elif "flask" in command.lower() or "web app" in command.lower():
            files_created = []
            
            # Create basic flask app from template
            for filename, content in self.templates["flask_app"].items():
                filepath = self.active_project.create_file(filename, content)
                files_created.append(filename)
            
            return {
                "success": True,
                "message": f"Built basic Flask web application in {self.active_project.name}",
                "files_created": files_created
            }
        
        # Default: create a Python file
        else:
            filename = "main.py"
            content = "# Auto-generated Python file\n\ndef main():\n    print('Hello from Dev Agent!')\n\nif __name__ == '__main__':\n    main()\n"
            filepath = self.active_project.create_file(filename, content)
            
            return {
                "success": True,
                "message": f"Created basic Python script in {self.active_project.name}",
                "filepath": filepath
            }
    
    def _run_code(self, command):
        """Run code in the active project"""
        if not self.active_project:
            return {
                "success": False,
                "message": "No active project. Create a project first."
            }
        
        # Determine what to run
        run_command = "python app.py"  # Default for Flask
        
        if "main.py" in self.active_project.files:
            run_command = "python main.py"
        
        # Run the command
        result = self.active_project.run_command(run_command)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Code ran successfully",
                "output": result["output"]
            }
        else:
            return {
                "success": False,
                "message": f"Error running code",
                "error": result["error"]
            }
    
    def _list_files(self):
        """List files in the active project"""
        if not self.active_project:
            return {
                "success": False,
                "message": "No active project. Create a project first."
            }
        
        files = self.active_project.list_files()
        
        return {
            "success": True,
            "message": f"Project '{self.active_project.name}' contains {len(files)} files",
            "files": files
        }
    
    def _show_file(self, filename):
        """Show content of a file"""
        if not self.active_project:
            return {
                "success": False,
                "message": "No active project. Create a project first."
            }
        
        content = self.active_project.read_file(filename)
        
        if content is None:
            return {
                "success": False,
                "message": f"File '{filename}' not found"
            }
        
        return {
            "success": True,
            "message": f"Content of '{filename}':",
            "filename": filename,
            "content": content
        }

def main():
    print("👨‍💻 Dev Agent: Voice-Interactive Coding Assistant")
    print("================================================")
    print("Using MCP-ZERO for traceable, auditable AI coding")
    
    agent = DevAgent()
    
    print("\nReady for coding commands!")
    print("Try commands like:")
    print("  - 'Create a new project called web_app'")
    print("  - 'Build a Flask app with login'")
    print("  - 'Run the code'")
    print("  - 'Show file app.py'")
    
    while True:
        command = input("\n🎙️ Say coding command: ")
        
        if command.lower() == "exit":
            print("Exiting Dev Agent. Goodbye!")
            break
            
        result = agent.process_command(command)
        
        print(f"\n🤖 {result['message']}")
        
        # Show additional information if available
        if result.get("output"):
            print("\nOutput:")
            print(result["output"])
            
        if result.get("error"):
            print("\nError:")
            print(result["error"])
            
        if result.get("content"):
            print("\nFile content:")
            print("```")
            print(result["content"])
            print("```")

if __name__ == "__main__":
    main()
