#!/usr/bin/env python3
"""
MCP-ZERO Creative Workflow Demo - Main Entry Point
Integrates all components to simulate a complete creative workflow
"""
import json
import logging
import time
import os
import sys
import argparse
from typing import Dict, Any, List

# Import our modules
from setup import ResourceMonitor
from creative_agents import ScriptAgent, VisualAgent, AudioAgent, EditorAgent
from creative_agreement import CreativeAgreement
from workflow_simulation import VideoProject, CreativeWorkflow
from scene_generation import SceneGenerator
from audio_generation import AudioGenerator
from video_editor import VideoEditor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("creative_demo")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='MCP-ZERO Creative Workflow Demo')
    parser.add_argument('--project-name', default='Harmony of Mind and Machine',
                       help='Name of the video project')
    parser.add_argument('--description', 
                       default='A short film about how AI and humans collaborate to solve climate change',
                       help='Description of the video project')
    parser.add_argument('--rpc-url', default='http://localhost:8082',
                       help='URL of the MCP-ZERO RPC server')
    parser.add_argument('--output-dir', 
                       default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"),
                       help='Output directory for generated assets')
    parser.add_argument('--mock', action='store_true',
                       help='Run in mock mode without RPC server')
    
    return parser.parse_args()

def print_demo_banner():
    """Print demo banner"""
    banner = """
    =======================================================================
                       MCP-ZERO CREATIVE WORKFLOW DEMO
    =======================================================================
    Simulating creative video production workflow with MCP-ZERO agents
    Respecting hardware constraints: <27% CPU, <827MB RAM
    Demonstrating Solidity-inspired agreements for governance
    """
    print(banner)

def run_complete_demo(args):
    """Run the complete creative workflow demo"""
    print_demo_banner()
    
    # Initialize resource monitor
    monitor = ResourceMonitor()
    
    # Create project
    logger.info(f"Creating project: {args.project_name}")
    project = VideoProject(args.project_name, args.description)
    
    # Set up creative workflow
    logger.info("Initializing creative workflow...")
    workflow = CreativeWorkflow(project)
    
    # Set up agents and register agreement
    logger.info("Setting up agents and agreement...")
    workflow.setup_agents()
    agreement_hash = workflow.create_agreement()
    logger.info(f"Creative agreement registered with hash: {agreement_hash}")
    
    # Step 1: Generate script
    logger.info("\n" + "="*50)
    logger.info("STEP 1: GENERATING SCRIPT")
    logger.info("="*50)
    script_result = workflow.generate_script()
    
    if "error" in script_result:
        logger.error(f"Script generation failed: {script_result['error']}")
        return False
    
    script = project.assets["script"]
    logger.info(f"Script generated successfully: {len(script)} chars")
    logger.info(f"Script excerpt: {script[:200]}...")
    
    # Step 2: Generate visual scenes
    logger.info("\n" + "="*50)
    logger.info("STEP 2: GENERATING VISUAL SCENES")
    logger.info("="*50)
    
    # Initialize scene generator with our agent ID
    scene_generator = SceneGenerator(
        workflow.visual_agent.agent_id,
        output_dir=args.output_dir
    )
    
    # Extract scenes from script
    scenes = scene_generator.extract_scene_descriptions(script)
    logger.info(f"Extracted {len(scenes)} scenes from script")
    
    # Generate visuals for each scene
    generated_scenes = []
    for scene in scenes:
        logger.info(f"Generating visual for scene: {scene['heading']}")
        
        # Check agreement compliance before generating
        action_params = {
            "resource_usage": monitor.report_usage(),
            "scene_content": scene['description']
        }
        
        if workflow.agreement and not workflow.agreement.verify_action(
            workflow.visual_agent.agent_id, "generate_visual", action_params):
            logger.error(f"Visual generation not permitted under agreement for scene {scene['id']}")
            continue
        
        # Generate the visual
        visual = scene_generator.generate_scene_visuals(scene)
        generated_scenes.append({**scene, **visual})
    
    # Save to project
    project.assets["scenes"] = generated_scenes
    project.update_status("visuals_completed")
    
    # Step 3: Generate audio soundtrack
    logger.info("\n" + "="*50)
    logger.info("STEP 3: GENERATING AUDIO")
    logger.info("="*50)
    
    # Initialize audio generator with our agent ID
    audio_generator = AudioGenerator(
        workflow.audio_agent.agent_id,
        output_dir=args.output_dir
    )
    
    # Analyze script mood
    mood_analysis = audio_generator.analyze_script_mood(script)
    logger.info(f"Script mood analysis: {mood_analysis['primary_mood']}")
    
    # Generate soundtrack - assume 2 minutes for demo
    estimated_duration = 120  # 2 minutes
    
    # Check agreement compliance before generating
    action_params = {
        "resource_usage": monitor.report_usage(),
        "duration": estimated_duration
    }
    
    if workflow.agreement and not workflow.agreement.verify_action(
        workflow.audio_agent.agent_id, "generate_audio", action_params):
        logger.error("Audio generation not permitted under agreement")
        return False
    
    # Generate the soundtrack
    soundtrack = audio_generator.generate_soundtrack(mood_analysis, estimated_duration)
    
    # Save to project
    project.assets["audio"] = soundtrack
    project.update_status("audio_completed")
    
    # Step 4: Edit and render final video
    logger.info("\n" + "="*50)
    logger.info("STEP 4: EDITING AND RENDERING VIDEO")
    logger.info("="*50)
    
    # Initialize video editor with our agent ID
    video_editor = VideoEditor(
        workflow.editor_agent.agent_id,
        output_dir=args.output_dir
    )
    
    # Create timeline
    timeline = video_editor.create_timeline(generated_scenes, soundtrack)
    logger.info(f"Created video timeline: {timeline['duration_seconds']}s duration")
    
    # Apply visual effects
    timeline = video_editor.apply_visual_effects(
        timeline,
        ["color_grading", "stabilization", "light_enhancement"]
    )
    
    # Check agreement compliance before rendering
    action_params = {
        "resource_usage": monitor.report_usage(),
        "timeline": {"duration": timeline["duration_seconds"]}
    }
    
    if workflow.agreement and not workflow.agreement.verify_action(
        workflow.editor_agent.agent_id, "render_video", action_params):
        logger.error("Video rendering not permitted under agreement")
        return False
    
    # Render the final video
    final_video = video_editor.render_final_video(timeline)
    
    # Save to project
    project.save_asset("final_video", final_video)
    project.update_status("completed")
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("DEMO COMPLETED SUCCESSFULLY")
    logger.info("="*50)
    logger.info(f"Project: {project.project_name}")
    logger.info(f"Duration: {final_video['duration']} seconds")
    logger.info(f"Resolution: {final_video['resolution']}")
    logger.info(f"Output file: {final_video['filename']}")
    logger.info(f"Agreement hash: {agreement_hash}")
    logger.info(f"Max resource usage: {monitor.get_max_usage()}")
    logger.info(f"All output files in: {args.output_dir}")
    
    # Save overall project metadata
    metadata_path = os.path.join(args.output_dir, f"project_{project.project_id}_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump({
            "project_name": project.project_name,
            "project_id": project.project_id,
            "description": project.description,
            "agreement_hash": agreement_hash,
            "workflow_status": project.workflow_status,
            "final_video": final_video,
            "resource_usage": monitor.get_max_usage(),
            "timestamp": time.time()
        }, f, indent=2)
    
    logger.info(f"Project metadata saved to: {metadata_path}")
    return True

if __name__ == "__main__":
    args = parse_arguments()
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        success = run_complete_demo(args)
        if success:
            exit_code = 0
        else:
            exit_code = 1
    except Exception as e:
        logger.exception(f"Demo failed with error: {e}")
        exit_code = 1
    
    sys.exit(exit_code)
