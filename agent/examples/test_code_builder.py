"""
Test script for CodeBuilderAgent

Run with:
    python test_code_builder.py

Tests:
1. Tool tests (no API needed)
2. Agent initialization test
3. Full build test (requires OPENAI_API_KEY)
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_builder_agent import (
    CodeBuilderAgent,
    CreateFileTool,
    WriteFileTool,
    ReadFileTool,
    DeleteFileTool,
    RunCodeTool,
    ListFilesTool,
)


# Test workspace
TEST_WORKSPACE = "./test_workspace"


def print_header(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(name: str, success: bool, message: str = ""):
    """Print test result"""
    icon = "✅" if success else "❌"
    print(f"{icon} {name}")
    if message:
        print(f"   {message}")


async def test_tools():
    """Test all file operation tools"""
    print_header("Testing Tools (No API Required)")
    
    # Clean up test workspace
    workspace = Path(TEST_WORKSPACE)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    
    all_passed = True
    
    # Test 1: Create File
    print("1. Testing create_file...")
    tool = CreateFileTool(TEST_WORKSPACE)
    result = await tool(path="test.py", content="print('Hello World')")
    success = result.success and (workspace / "test.py").exists()
    print_result("create_file", success, result.data if success else result.error_message)
    all_passed = all_passed and success
    
    # Test 2: Read File
    print("\n2. Testing read_file...")
    tool = ReadFileTool(TEST_WORKSPACE)
    result = await tool(path="test.py")
    success = result.success and "Hello World" in result.data
    print_result("read_file", success, f"Content: {result.data[:50]}..." if success else result.error_message)
    all_passed = all_passed and success
    
    # Test 3: Write File
    print("\n3. Testing write_file...")
    tool = WriteFileTool(TEST_WORKSPACE)
    result = await tool(path="test.py", content="print('Updated!')")
    success = result.success
    print_result("write_file", success, result.data if success else result.error_message)
    
    # Verify content was updated
    read_tool = ReadFileTool(TEST_WORKSPACE)
    read_result = await read_tool(path="test.py")
    success = read_result.success and "Updated" in read_result.data
    print_result("  verify content", success)
    all_passed = all_passed and success
    
    # Test 4: Run Code
    print("\n4. Testing run_code...")
    tool = RunCodeTool(TEST_WORKSPACE)
    
    # Test running file
    result = await tool(path="test.py")
    success = result.success and "Updated" in result.data
    print_result("run_code (file)", success, result.data[:100] if success else result.error_message)
    all_passed = all_passed and success
    
    # Test running code directly
    result = await tool(code="print(2 + 2)")
    success = result.success and "4" in result.data
    print_result("run_code (direct)", success, result.data[:100] if success else result.error_message)
    all_passed = all_passed and success
    
    # Test 5: List Files
    print("\n5. Testing list_files...")
    tool = ListFilesTool(TEST_WORKSPACE)
    result = await tool()
    success = result.success and "test.py" in result.data
    print_result("list_files", success, result.data if success else result.error_message)
    all_passed = all_passed and success
    
    # Test 6: Create nested file
    print("\n6. Testing nested file creation...")
    tool = CreateFileTool(TEST_WORKSPACE)
    result = await tool(path="src/utils/helper.py", content="# Helper module")
    success = result.success and (workspace / "src/utils/helper.py").exists()
    print_result("create nested file", success, result.data if success else result.error_message)
    all_passed = all_passed and success
    
    # Test 7: Delete File
    print("\n7. Testing delete_file...")
    tool = DeleteFileTool(TEST_WORKSPACE)
    result = await tool(path="test.py")
    success = result.success and not (workspace / "test.py").exists()
    print_result("delete_file", success, result.data if success else result.error_message)
    all_passed = all_passed and success
    
    # Summary
    print(f"\n{'─'*60}")
    if all_passed:
        print("✅ All tool tests passed!")
    else:
        print("❌ Some tool tests failed")
    
    return all_passed


async def test_agent_init():
    """Test agent initialization"""
    print_header("Testing Agent Initialization")
    
    try:
        agent = CodeBuilderAgent(
            api_key="test-key",  # Fake key for init test
            model="gpt-4",
            workspace=TEST_WORKSPACE,
        )
        
        await agent.initialize()
        
        # Check components
        checks = [
            ("Agent created", agent is not None),
            ("Planner initialized", agent.planner is not None),
            ("Reasoner initialized", agent.reasoner is not None),
            ("Memory initialized", agent.memory is not None),
            ("Tools registered", len(agent.tools.get_all()) == 6),
        ]
        
        all_passed = True
        for name, passed in checks:
            print_result(name, passed)
            all_passed = all_passed and passed
        
        # List tools
        print("\n📦 Registered tools:")
        for tool in agent.tools.get_all():
            print(f"   - {tool.name}")
        
        # Check status
        print("\n📊 Agent status:")
        status = agent.get_status()
        print(f"   Name: {status['name']}")
        print(f"   State: {status['state']}")
        print(f"   Has plan: {status['plan']['has_plan']}")
        
        print(f"\n{'─'*60}")
        if all_passed:
            print("✅ Agent initialization test passed!")
        else:
            print("❌ Agent initialization test failed")
        
        return all_passed
        
    except Exception as e:
        print_result("Agent initialization", False, str(e))
        return False


async def test_full_build():
    """Test full build with real API (requires OPENAI_API_KEY)"""
    print_header("Testing Full Build (Requires API Key)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set - skipping full build test")
        print("   Set with: export OPENAI_API_KEY='your-key'")
        return None
    
    # Clean workspace
    workspace = Path(TEST_WORKSPACE)
    if workspace.exists():
        shutil.rmtree(workspace)
    
    try:
        # Create agent
        agent = CodeBuilderAgent(
            api_key=api_key,
            model="gpt-4",
            workspace=TEST_WORKSPACE,
        )
        
        await agent.initialize()
        
        # Simple test task
        print("🔨 Building a simple hello world program...\n")
        
        result = await agent.build(
            task="Create a simple Python file called hello.py that prints 'Hello from CodeBuilder!' and run it to verify",
            constraints=["Keep it simple", "Just one file"],
        )
        
        # Check results
        success = result["success"]
        
        print(f"\n{'─'*60}")
        if success:
            print("✅ Full build test passed!")
            
            # Verify file exists
            hello_file = workspace / "hello.py"
            if hello_file.exists():
                print(f"\n📄 Created file content:")
                print(f"{'─'*40}")
                print(hello_file.read_text())
                print(f"{'─'*40}")
        else:
            print("❌ Full build test failed")
            print(f"   Error: {result.get('status', {}).get('error', 'Unknown')}")
        
        return success
        
    except Exception as e:
        print(f"❌ Full build test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory():
    """Test memory system"""
    print_header("Testing Memory System")
    
    agent = CodeBuilderAgent(
        api_key="test-key",
        workspace=TEST_WORKSPACE,
    )
    await agent.initialize()
    
    all_passed = True
    
    # Test short-term memory
    print("1. Testing short-term memory...")
    agent.memory.remember("Test message 1", memory_type="short")
    agent.memory.remember("Test message 2", memory_type="short")
    results = agent.memory.recall("Test message", sources=["short"])
    success = len(results) >= 2
    print_result("Short-term memory", success, f"Found {len(results)} items")
    all_passed = all_passed and success
    
    # Test long-term memory
    print("\n2. Testing long-term memory...")
    agent.memory.remember("Important info", memory_type="long", importance=0.9)
    results = agent.memory.recall("Important", sources=["long"])
    success = len(results) >= 1
    print_result("Long-term memory", success, f"Found {len(results)} items")
    all_passed = all_passed and success
    
    # Test working memory
    print("\n3. Testing working memory...")
    agent.memory.working.set_task("test_task")
    agent.memory.working.set("key1", "value1")
    agent.memory.working.add_step(thought="Test thought", action="test", observation="Test obs")
    
    success = (
        agent.memory.working.get("key1") == "value1" and
        len(agent.memory.working.get_history()) == 1
    )
    print_result("Working memory", success)
    all_passed = all_passed and success
    
    # Test memory stats
    print("\n📊 Memory stats:")
    stats = agent.memory.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n{'─'*60}")
    if all_passed:
        print("✅ Memory tests passed!")
    else:
        print("❌ Some memory tests failed")
    
    return all_passed


async def test_plan_tracking():
    """Test plan tracking (without actual execution)"""
    print_header("Testing Plan Tracking")
    
    agent = CodeBuilderAgent(
        api_key="test-key",
        workspace=TEST_WORKSPACE,
    )
    await agent.initialize()
    
    # Manually create a plan for testing
    from utils import Plan, PlanStep, StepStatus
    
    plan = Plan(task="Test task")
    plan.add_step(PlanStep(step_id=1, description="Step 1", action="think"))
    plan.add_step(PlanStep(step_id=2, description="Step 2", action="create_file", dependencies=[1]))
    plan.add_step(PlanStep(step_id=3, description="Step 3", action="run_code", dependencies=[2]))
    
    agent._current_plan = plan
    
    all_passed = True
    
    # Test status
    print("1. Testing plan status...")
    status = agent.get_plan_status()
    success = (
        status["has_plan"] == True and
        status["total_steps"] == 3 and
        status["progress"] == 0.0
    )
    print_result("Initial status", success)
    all_passed = all_passed and success
    
    # Test progress tracking
    print("\n2. Testing progress tracking...")
    plan.steps[0].status = StepStatus.COMPLETED
    status = agent.get_plan_status()
    success = status["completed_steps"] == 1 and status["progress"] > 0
    print_result("After step 1", success, f"Progress: {status['progress_percent']}")
    all_passed = all_passed and success
    
    plan.steps[1].status = StepStatus.COMPLETED
    status = agent.get_plan_status()
    success = status["completed_steps"] == 2
    print_result("After step 2", success, f"Progress: {status['progress_percent']}")
    all_passed = all_passed and success
    
    # Test print_plan
    print("\n3. Testing print_plan...")
    plan_str = agent.print_plan()
    success = "Step 1" in plan_str and "✅" in plan_str
    print_result("print_plan", success)
    print(f"\n{plan_str}")
    all_passed = all_passed and success
    
    # Test details
    print("\n4. Testing get_plan_details...")
    details = agent.get_plan_details()
    success = details is not None and len(details["steps"]) == 3
    print_result("get_plan_details", success)
    all_passed = all_passed and success
    
    print(f"\n{'─'*60}")
    if all_passed:
        print("✅ Plan tracking tests passed!")
    else:
        print("❌ Some plan tracking tests failed")
    
    return all_passed


async def cleanup():
    """Clean up test workspace"""
    workspace = Path(TEST_WORKSPACE)
    if workspace.exists():
        shutil.rmtree(workspace)
        print(f"\n🧹 Cleaned up test workspace: {TEST_WORKSPACE}")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  CodeBuilderAgent Test Suite")
    print("="*60)
    
    results = {}
    
    # Run tests
    results["tools"] = await test_tools()
    results["agent_init"] = await test_agent_init()
    results["memory"] = await test_memory()
    results["plan_tracking"] = await test_plan_tracking()
    results["full_build"] = await test_full_build()
    
    # Summary
    print_header("Test Summary")
    
    for name, result in results.items():
        if result is None:
            print(f"⏭️  {name}: Skipped")
        elif result:
            print(f"✅ {name}: Passed")
        else:
            print(f"❌ {name}: Failed")
    
    # Count results
    passed = sum(1 for r in results.values() if r == True)
    failed = sum(1 for r in results.values() if r == False)
    skipped = sum(1 for r in results.values() if r is None)
    
    print(f"\n{'─'*60}")
    print(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")
    
    # Cleanup
    await cleanup()
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

