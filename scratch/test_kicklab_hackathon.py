import os
import asyncio
import json
from app.graph.workflow import execute_run_task
from app.workspace.manager import get_workspace_manager
from app.workspace.web_server import get_web_server_manager

async def run_kicklab_hackathon_test():
    ws = get_workspace_manager()
    objective = (
        "Build me a complete modern ecommerce website for KICKLAB. "
        "It should have: premium navigation, hero section, product grid, at least 8 sneaker products, "
        "product categories, search, filtering, shopping cart, cart count, add/remove quantity, "
        "responsive mobile layout, newsletter, footer, polished modern UI. "
        "Use separate HTML, CSS and JavaScript files. Link them correctly. "
        "Inspect and validate the files. Then run/preview the application inside Fraiday."
    )

    run_id = "hackathon_kicklab_test"
    runs_db = {
        run_id: {
            "run_id": run_id,
            "objective": objective,
            "status": "pending",
            "state": {}
        }
    }

    print("Starting Fraiday Autonomous Workflow for KICKLAB Ecommerce...")
    await execute_run_task(run_id, objective, runs_db)

    final_run = runs_db[run_id]
    final_state = final_run.get("state", {})

    print("\n--- WORKFLOW EXECUTION COMPLETE ---")
    print(f"Run Status: {final_run.get('status')}")
    print(f"Plan Steps Executed: {len(final_state.get('plan', []))}")
    
    # Check generated files
    html_p = ws.resolve_path("ecommerce.html")
    css_p = ws.resolve_path("ecommerce.css")
    js_p = ws.resolve_path("ecommerce.js")

    print(f"\necommerce.html exists: {os.path.exists(html_p)} ({os.path.getsize(html_p) if os.path.exists(html_p) else 0} bytes)")
    print(f"ecommerce.css exists:  {os.path.exists(css_p)} ({os.path.getsize(css_p) if os.path.exists(css_p) else 0} bytes)")
    print(f"ecommerce.js exists:   {os.path.exists(js_p)} ({os.path.getsize(js_p) if os.path.exists(js_p) else 0} bytes)")

    # Check validation results
    vals = final_state.get("validation_results", [])
    if vals:
        last_val = vals[-1]
        print(f"\nValidation Result: VALID={last_val.get('valid')} STATUS={last_val.get('status')} REASON={last_val.get('reason')}")
    
    # Test preview server lifecycle
    server_mgr = get_web_server_manager()
    srv_res = server_mgr.start(ws.root_path, preferred_port=5500)
    print(f"\nPreview Server Status: {srv_res.get('status')} | URL: {srv_res.get('url')}/ecommerce.html")

if __name__ == "__main__":
    asyncio.run(run_kicklab_hackathon_test())
