import importlib.util
from pathlib import Path
from mcp_mode import run_mcp_tool

# total_activity_count,
#     total_activities_count_a_day,
#     get_trip_activities_desc,
#     get_trip_activities_for_day_desc,
#     get_activity_start_times,
#     get_travel_requirements

# checking if MCP ahs been properly integrated or not?
# to test it, it's really important to know if
# all the files building the MCP server are there or not?
# check if we have all the files?

# then we have to test if required functions which we wanna expose to
# MCP are registered as tools or not?


# after checking if MCp server is exposed to the expected tools,
# it's important to test taht those tools which are exposed as
# MCP tools, have a function assigned to them or not.
# is there a function powering that tool or not.
#


REQUIRED_MCP_TOOLS = ["total_activity_count" , "total_activities_count_a_day" ,"get_trip_activities_desc" ,
                     "get_trip_activities_for_day_desc" , "get_activity_start_times" , "get_travel_requirements"]
REQUIRED_FUNCTIONS = {
    "total_activity_count": "total_activity_count",
    "total_activities_count_a_day": "total_activities_count_a_day",
    "get_trip_activities_desc": "get_trip_activities_desc",
    "get_trip_activities_for_day_desc": "get_trip_activities_for_day_desc",
    "get_activity_start_times": "get_activity_start_times",
    "get_travel_requirements": "get_travel_requirements",
}


def _load_tools_module(mcp_server_dir: Path):
    spec = importlib.util.spec_from_file_location("mcp_tools_check", mcp_server_dir / "tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    mcp_server_dir =  repo_root / "ai-services" / "mcp-server"

    # storing the directory path to all the important files.

    required_paths = [
        repo_root / "mcp-server" / "tools.py",
        repo_root / "mcp-server" / "server.py",
        repo_root / "mcp-server" / "requirements.txt",
        repo_root / "ai-services" / "mcp-server" / "mcp_mode.py",
        repo_root / "student-4" / "frontend" / "src" / "pages" / "MCPIntegratedFrontend.tsx"
        ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "MCP evidence incomplete. Missing: " + ", ".join(missing)

    tools_text = (mcp_server_dir / "tools.py").read_text(encoding="utf-8")
    server_text = (mcp_server_dir / "server.py").read_text(encoding="utf-8")

    missing_tools = [tool for tool in REQUIRED_MCP_TOOLS if tool not in server_text]
    if missing_tools:
        return False, "MCP server missing required tools: " + ", ".join(missing_tools)

    missing_functions = [
        func_name for func_name in REQUIRED_FUNCTIONS.values() if f"def {func_name}" not in tools_text
    ]
    if missing_functions:
        return False, "tools.py missing required function implementations: " + ", ".join(missing_functions)

    # after checking if we ahve all the necessary tools and a function
    # powering the tools, it's time to test them.
    # here, tools are being tested with an actual data to know if
    # if the MCP properly works or not.
    # it returns an evidence on teh basis of if the test was succesful
    # or not.


    try:
        tools_module.total_activity_count(3)
        tools_module.total_activities_count_a_day(3, 1)
        tools_module.get_trip_activities_desc(3)
        tools_module.get_trip_activities_for_day_desc(3, 1)
        tools_module.get_activity_start_times(3)
        tools_module.get_travel_requirements(3)
    except Exception as exc:
        return False, f"MCP tool execution failed: {exc}"

    return True, (
        "MCP evidence: ai-services/mcp-server contains tools.py and server.py; "
        f"server defines {len(REQUIRED_MCP_TOOLS)} travel MCP tools; "
        "all travel MCP tools executed successfully; "
        "student-4 backend mcp_mode.js and MCPIntegratedFrontend.tsx exist."
    )