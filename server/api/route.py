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

    # If workflow returns SummaryAgentOutputSchema, extract cleanly
    if isinstance(result, dict):
        summary = result.get("summary")
        status = result.get("status", "unknown")
    else:
        summary = str(result)
        status = "unknown"

    return {
        "query": user_query.query,
        "output": {
            "summary": summary,
            "status": status,
            "format": "markdown"
        }
    }
