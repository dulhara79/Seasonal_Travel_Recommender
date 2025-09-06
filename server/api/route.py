from fastapi import APIRouter
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.schemas.userQuery_schema import UserQuerySchema
from server.workflow.graph_builder import build_graph

router = APIRouter()
workflow = build_graph()

# @router.post("/chat")
# def chat(user_query: UserQuerySchema):
#     # wrap user input into orchestrator input schema
#     orchestrator_input = OrchestratorAgent4InputSchema(query=user_query.query)
#
#     # run the graph
#     result = workflow.invoke(orchestrator_input)
#
#     # Ensure we get the summary if available
#     summary = None
#     if isinstance(result, dict):
#         summary = result.get("summary")  # SummaryAgentOutputSchema field
#
#     return {
#         "query": user_query.query,
#         "output": {
#             "summary": summary if summary else result,
#             "format": "markdown"
#         }
#     }

@router.post("/chat")
def chat(user_query: UserQuerySchema):
    orchestrator_input = OrchestratorAgent4InputSchema(query=user_query.query)

    # run the workflow
    result = workflow.invoke(orchestrator_input)

    print(f"\n======\nWorkflow result: {result}")

    # Normalize result to extract summary and status reliably.
    summary = None
    status = "unknown"

    # Case 1: result is a dict (could be orchestrator output, activity output or summary output)
    if isinstance(result, dict):
        # Direct summary field
        if "summary" in result:
            summary = result.get("summary")
            status = result.get("status", status)
        else:
            # Maybe the last node returned a nested dict (e.g., activity -> summary)
            # Try common keys
            for key in ("output", "result", "data"):
                if isinstance(result.get(key), dict) and "summary" in result.get(key):
                    summary = result.get(key).get("summary")
                    status = result.get(key).get("status", status)
                    break
            # As a fallback, if the dict contains only primitive keys, stringify it
            if summary is None:
                # Try to find any string value that looks like a markdown summary
                for v in result.values():
                    if isinstance(v, str) and v.strip().startswith("#"):
                        summary = v
                        break
                # Last resort: stringify the whole dict
                if summary is None:
                    summary = str(result)

    else:
        # Non-dict results (could be pydantic model or plain string)
        try:
            # Pydantic models have dict() or model_dump()
            if hasattr(result, "model_dump"):
                rd = result.model_dump()
            elif hasattr(result, "dict"):
                rd = result.dict()
            else:
                rd = None

            if isinstance(rd, dict):
                summary = rd.get("summary") or rd.get("output") or str(rd)
                status = rd.get("status", status)
            else:
                summary = str(result)
        except Exception:
            summary = str(result)

    return {
        "query": user_query.query,
        "output": {
            "summary": summary,
            "status": status,
            "format": "markdown"
        }
    }


######
##  https://chat.deepseek.com/a/chat/s/aa21272b-9b60-44fb-8957-68113106d281
#######