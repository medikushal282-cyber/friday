# Fraiday - Workflow Architecture

Fraiday operates on a Directed Acyclic Graph (DAG) state machine for execution tasks.

## Nodes
1. **Orchestrator**: Decomposes user objective into a structured JSON plan of steps.
2. **Researcher**: (Optional) Gathers context if the orchestrator requests it before finalizing the plan.
3. **Executor**: Executes the steps sequentially, invoking the appropriate tools and handling human approval pauses.
4. **Validator**: Inspects the final state to ensure the objective was met.
5. **Recovery**: If a step fails, analyzes the error and replans or fixes the issue automatically.
6. **Controller**: The edge router that decides which node to transition to next (e.g. from Executor back to Executor for next step, or to Validator if done).

## Execution Loop
`Objective -> Orchestrator -> [Plan] -> Executor(Step 1) -> Executor(Step 2) -> ... -> Validator -> Done`
