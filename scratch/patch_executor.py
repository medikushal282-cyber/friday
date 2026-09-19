with open('backend/app/graph/nodes/executor.py', 'r') as f:
    content = f.read()

patch = """        elif action == "RUN_BACKGROUND_COMMAND":
            cmd = args.get("command")
            cwd_arg = args.get("cwd", ".")
            await emit(run_id, "tool_call_started", "executor", {"tool": "run_background_command", "command": cmd})
            res = await asyncio.to_thread(execute_action, {"tool": "run_background_command", "arguments": {"command": cmd, "cwd": cwd_arg}})
            await emit(run_id, "tool_call_completed", "executor", res)
            state.setdefault("tool_calls", []).append({"action": {"tool": "run_background_command", "arguments": {"command": cmd, "cwd": cwd_arg}}, "result": res})
            step["result"] = res
            step["status"] = "completed" if res.get("success") else "failed"
            await emit(run_id, "step_completed" if res.get("success") else "step_failed", "executor", {"step_id": step_id, "status": step["status"]})

        elif action == "MANAGE_BACKGROUND_TERMINAL":
            t_id = args.get("terminal_id")
            m_action = args.get("action")
            await emit(run_id, "tool_call_started", "executor", {"tool": "manage_background_terminal", "terminal_id": t_id, "action": m_action})
            res = await asyncio.to_thread(execute_action, {"tool": "manage_background_terminal", "arguments": {"terminal_id": t_id, "action": m_action}})
            await emit(run_id, "tool_call_completed", "executor", res)
            state.setdefault("tool_calls", []).append({"action": {"tool": "manage_background_terminal", "arguments": {"terminal_id": t_id, "action": m_action}}, "result": res})
            step["result"] = res
            step["status"] = "completed" if res.get("success") else "failed"
            await emit(run_id, "step_completed" if res.get("success") else "step_failed", "executor", {"step_id": step_id, "status": step["status"]})

        else:"""

content = content.replace("        else:", patch)

with open('backend/app/graph/nodes/executor.py', 'w') as f:
    f.write(content)
