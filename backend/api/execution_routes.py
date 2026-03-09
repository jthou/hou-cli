"""执行审批 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.infrastructure.execution.approval import get_approval_manager

router = APIRouter(prefix="/execution", tags=["execution"])


class ApproveRequest(BaseModel):
    """审批请求"""
    approval_id: str


class ApproveResponse(BaseModel):
    """审批响应"""
    approval_token: str
    approval_id: str


@router.post("/approve", response_model=ApproveResponse)
def approve_execution(req: ApproveRequest):
    """
    用户确认后，审批通过，返回 approval_token。
    前端在用户点击确认后调用此接口，然后将 token 随 execute_code 重试传入。
    """
    manager = get_approval_manager()
    try:
        token = manager.approve(req.approval_id)
        return ApproveResponse(approval_token=token, approval_id=req.approval_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class RejectRequest(BaseModel):
    approval_id: str


@router.post("/reject")
def reject_execution(req: RejectRequest):
    """用户拒绝审批"""
    manager = get_approval_manager()
    manager.reject(req.approval_id)
    return {"status": "rejected"}
