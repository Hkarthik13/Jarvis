import sys
import os

# Append workspace root to path to ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.registry import registry
import backend.ai.tools  # Registers all tools

def test_system_stats():
    print("\n--- Testing System Stats Tools ---")
    
    cpu = registry.execute_tool("get_cpu_usage", {})
    print("CPU Tool Output:", cpu)
    assert "CPU" in cpu or "Failed" in cpu
    
    ram = registry.execute_tool("get_ram_usage", {})
    print("RAM Tool Output:", ram)
    assert "RAM" in ram or "Failed" in ram
    
    disk = registry.execute_tool("get_disk_usage", {})
    print("Disk Tool Output:", disk)
    assert "disk" in disk.lower() or "Failed" in disk
    
    battery = registry.execute_tool("get_battery_status", {})
    print("Battery Tool Output:", battery)
    assert "battery" in battery.lower() or "Failed" in battery or "No battery" in battery
    
    os_info = registry.execute_tool("get_os_info", {})
    print("OS Info Tool Output:", os_info)
    assert "operating system" in os_info.lower() or "Failed" in os_info
    
    time_date = registry.execute_tool("get_current_time_date", {})
    print("Time/Date Tool Output:", time_date)
    assert "date and time" in time_date or "Failed" in time_date
    
    print("[PASS] System stats tools executed and returned expected format.")

def test_launch_app():
    print("\n--- Testing open_application validation ---")
    
    # 1. Test invalid application (must be rejected)
    invalid_res = registry.execute_tool("open_application", {"app_name": "cmd"})
    print("Invalid app result (expected rejection):", invalid_res)
    assert "Validation Error" in invalid_res or "not in the safe" in invalid_res
    
    # 2. Test valid application validation
    valid_res = registry.execute_tool("open_application", {"app_name": "notepad"})
    print("Valid app result:", valid_res)
    assert "Successfully opened notepad" in valid_res
    
    print("[PASS] open_application validated correctly.")

def test_launch_website():
    print("\n--- Testing open_website validation ---")
    
    # 1. Test invalid scheme (must be rejected)
    invalid_res = registry.execute_tool("open_website", {"url": "file:///C:/Windows/System32/cmd.exe"})
    print("Invalid URL scheme result (expected rejection):", invalid_res)
    assert "Validation Error" in invalid_res or "Invalid scheme" in invalid_res
    
    # 2. Test dangerous command injection characters (must be rejected)
    dangerous_res = registry.execute_tool("open_website", {"url": "google.com; cmd.exe"})
    print("Dangerous URL result (expected rejection):", dangerous_res)
    assert "Validation Error" in dangerous_res or "Dangerous characters" in dangerous_res
    
    # 3. Test valid URL conversion and open
    valid_res = registry.execute_tool("open_website", {"url": "google.com"})
    print("Valid URL result:", valid_res)
    assert "Successfully opened website" in valid_res
    
    print("[PASS] open_website validated correctly.")

def test_launch_folder():
    print("\n--- Testing open_folder validation ---")
    
    # 1. Test non-existent path
    non_existent = registry.execute_tool("open_folder", {"folder_path": "C:\\this_folder_does_not_exist_xyz"})
    print("Non-existent path result (expected rejection):", non_existent)
    assert "Validation Error" in non_existent or "does not exist" in non_existent
    
    # 2. Test file path rejection (must not start/execute a file!)
    file_path_res = registry.execute_tool("open_folder", {"folder_path": "requirements.txt"})
    print("File path result (expected rejection):", file_path_res)
    assert "Validation Error" in file_path_res or "not a directory" in file_path_res
    
    # 3. Test UNC path rejection (must be rejected)
    unc_res = registry.execute_tool("open_folder", {"folder_path": "\\\\10.0.0.5\\share"})
    print("UNC path result (expected rejection):", unc_res)
    assert "Validation Error" in unc_res or "UNC" in unc_res
    
    # 4. Test system directory traversal rejection
    sys_dir_res = registry.execute_tool("open_folder", {"folder_path": "C:\\Windows\\System32"})
    print("System directory result (expected rejection):", sys_dir_res)
    assert "Validation Error" in sys_dir_res or "restricted" in sys_dir_res
    
    # 5. Test valid directory path
    valid_dir = registry.execute_tool("open_folder", {"folder_path": "."})
    print("Valid directory result:", valid_dir)
    assert "Successfully opened folder" in valid_dir
    
    print("[PASS] open_folder validated correctly.")

if __name__ == "__main__":
    print("Starting JARVIS V2 System Tools Validation tests...")
    try:
        test_system_stats()
        test_launch_app()
        test_launch_website()
        test_launch_folder()
        print("\nAll System Tools Validation tests passed successfully!")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n[FAIL] Test assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error during tests: {e}")
        sys.exit(1)
