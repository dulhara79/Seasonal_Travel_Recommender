from fastapi import APIRouter
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.schemas.userQuery_schema import UserQuerySchema
from server.workflow.graph_builder import build_graph

router = APIRouter()
workflow = build_graph()

from fastapi import APIRouter
from server.schemas.userQuery_schema import UserQuerySchema
from server.workflow.graph_builder import build_graph
from server.schemas.global_schema import TravelState

router = APIRouter()
workflow = build_graph()

# @router.post("/chat")
# def chat(user_query: UserQuerySchema):
#     # Initialize the TravelState with the user query
#     state = TravelState(
#         messages=[{"role": "user", "content": user_query.query}],
#         additional_info=user_query.query
#     )
#
#     # Run the workflow
#     result = workflow.invoke(state)
#
#     print(f"\n======\nWorkflow result: {result}")
#
#     # Normalize result to extract summary and status reliably.
#     summary = None
#     status = "unknown"
#
#     if isinstance(result, dict):
#         # Direct summary field
#         if "summary" in result:
#             summary = result.get("summary")
#             status = result.get("status", status)
#         else:
#             # Try nested keys
#             for key in ("output", "result", "data"):
#                 if isinstance(result.get(key), dict) and "summary" in result.get(key):
#                     summary = result.get(key).get("summary")
#                     status = result.get(key).get("status", status)
#                     break
#             if summary is None:
#                 summary = str(result)
#     elif hasattr(result, "dict"):
#         rd = result.dict()
#         summary = rd.get("summary") or str(rd)
#         status = rd.get("status", status)
#     elif hasattr(result, "model_dump"):
#         rd = result.model_dump()
#         summary = rd.get("summary") or str(rd)
#         status = rd.get("status", status)
#     else:
#         summary = str(result)
#
#     return {
#         "query": user_query.query,
#         "output": {
#             "summary": summary,
#             "status": status,
#             "format": "markdown"
#         }
#     }

@router.post("/chat")
def chat(user_query: UserQuerySchema):
    # Initialize TravelState with user input
    state = TravelState(
        messages=[{"role": "user", "content": user_query.query}],
        additional_info=user_query.query
    )

    # Run the workflow
    result = workflow.invoke(state)

    # Extract summary and status reliably
    summary = None
    status = "unknown"

    if isinstance(result, dict):
        summary = result.get("summary") or str(result)
        status = result.get("status", "complete" if "summary" in result else "unknown")
    elif hasattr(result, "dict"):
        rd = result.dict()
        summary = rd.get("summary") or str(rd)
        status = rd.get("status", "unknown")

    return {
        "query": user_query.query,
        "output": {
            "summary": summary,
            "status": status,
            "format": "markdown"
        }
    }
