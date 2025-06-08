#!/usr/bin/env python3
"""
MCP-ZERO Creative Workflow Demo - Automated Tests
Tests the full workflow with mock RPC server to ensure CI/CD compatibility
"""
import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import demo components
from setup import ResourceMonitor
from workflow_simulation import CreativeWorkflow
from scene_generation import SceneGenerator
from audio_generation import AudioGenerator
from video_editor import VideoEditor
import run_creative_demo

class TestCreativeWorkflow(unittest.TestCase):
    """Test cases for the creative workflow demo"""
    
    def setUp(self):
        """Set up test environment"""
        # Create output directory if not exists
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"), exist_ok=True)
        # Initialize resource monitor
        self.resource_monitor = ResourceMonitor()
        # Mock RPC API responses
        self.patcher = patch('requests.post')
        self.mock_post = self.patcher.start()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_response.json.return_value = {"success": True, "data": {"id": "test-id-1234"}}
        self.mock_post.return_value = self.mock_response
        
    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()
    
    def test_resource_monitor(self):
        """Test that resource monitoring stays within MCP-ZERO limits"""
        monitor = ResourceMonitor()
        usage = monitor.report_usage()
        
        # Test resource constraints
        self.assertLess(usage["cpu_percent"], 27, "CPU usage exceeds MCP-ZERO limit")
        self.assertLess(usage["memory_mb"], 827, "Memory usage exceeds MCP-ZERO limit")
        
        # Test max usage tracking
        max_usage = monitor.get_max_usage()
        self.assertGreaterEqual(max_usage["cpu_percent"], usage["cpu_percent"])
        self.assertGreaterEqual(max_usage["memory_mb"], usage["memory_mb"])
    
    def test_workflow_initialization(self):
        """Test that the workflow initializes correctly"""
        workflow = CreativeWorkflow(
            project_name="Test Project",
            project_description="Test Description",
            resource_monitor=self.resource_monitor
        )
        
        self.assertEqual(workflow.project_name, "Test Project")
        self.assertEqual(workflow.project_description, "Test Description")
        self.assertIsNotNone(workflow.project_id)
        
    def test_script_generation(self):
        """Test script generation component"""
        workflow = CreativeWorkflow(
            project_name="Test Project",
            project_description="Test Description",
            resource_monitor=self.resource_monitor
        )
        
        script = workflow.generate_script()
        
        self.assertIsNotNone(script)
        self.assertGreater(len(script), 0)
        
    def test_scene_generation(self):
        """Test scene generation component"""
        scene_gen = SceneGenerator(self.resource_monitor)
        
        test_script = """
        TITLE: TEST SCRIPT
        
        FADE IN:
        
        EXT. TEST SCENE - DAY
        
        A test scene description.
        """
        
        scenes = scene_gen.extract_scenes(test_script)
        
        self.assertGreaterEqual(len(scenes), 1)
        self.assertIn("TEST SCENE", scenes[0]["description"])
        
    def test_audio_generation(self):
        """Test audio generation component"""
        audio_gen = AudioGenerator(self.resource_monitor)
        
        test_script = "This is a happy test script."
        
        mood = audio_gen.analyze_mood(test_script)
        self.assertIsNotNone(mood)
        
        soundtrack_meta = audio_gen.generate_soundtrack(mood, 60)
        self.assertIsNotNone(soundtrack_meta)
        self.assertEqual(soundtrack_meta["duration"], 60)
        
    def test_video_editor(self):
        """Test video editor component"""
        editor = VideoEditor(self.resource_monitor)
        
        scenes = [{
            "id": "scene-1",
            "description": "Test Scene",
            "visual_path": "simulated_path.jpg"
        }]
        
        soundtrack = {
            "id": "soundtrack-1",
            "mood": "test",
            "duration": 60
        }
        
        timeline = editor.create_timeline(scenes, soundtrack)
        self.assertIsNotNone(timeline)
        
        effects_result = editor.apply_visual_effects(timeline)
        self.assertTrue(effects_result)
        
        video_data = editor.render_video(timeline, resolution="720p")
        self.assertIsNotNone(video_data)
        self.assertIn("filename", video_data)
        
    def test_agreement_verification(self):
        """Test that agreement verification works properly"""
        workflow = CreativeWorkflow(
            project_name="Test Project",
            project_description="Test Description",
            resource_monitor=self.resource_monitor
        )
        
        result = workflow.verify_against_agreement("test_action", {"resource": "test"})
        self.assertTrue(result)
        
    def test_full_demo_mock_mode(self):
        """Test full demo execution in mock mode"""
        # Patch sys.argv to use mock mode
        with patch('sys.argv', ['run_creative_demo.py', '--mock']):
            result = run_creative_demo.main()
            self.assertEqual(result, 0)

if __name__ == "__main__":
    unittest.main()
