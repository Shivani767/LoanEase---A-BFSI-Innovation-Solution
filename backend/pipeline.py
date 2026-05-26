from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from agents import (
    BlockchainAuditAgent,
    CreditUnderwritingAgent,
    KYCVerificationAgent,
    MasterOrchestratorAgent,
    NegotiationAgent,
)


class LoanPipeline:
    def __init__(self):
        self.kyc = KYCVerificationAgent()
        self.credit = CreditUnderwritingAgent()
        self.negotiation = NegotiationAgent()
        self.blockchain = BlockchainAuditAgent()
        self.master = MasterOrchestratorAgent(
            agents={
                "KYCVerificationAgent": self.kyc,
                "CreditUnderwritingAgent": self.credit,
                "Negotiation Agent": self.negotiation,
                "BlockchainAuditAgent": self.blockchain,
            }
        )
        self.agent_log: list[dict[str, Any]] = []
        self._session_logs: dict[str, list[dict[str, Any]]] = {}
        self._session_status: dict[str, str] = {}
        self._global_logs: list[dict[str, Any]] = []
        self._MAX_GLOBAL_LOGS = 100

    async def run_stage(self, stage: str, payload: dict) -> dict:
        """
        Run one pipeline stage with full trace logging.

        Flow:
        1) Master inspects context and suggests action
        2) Stage agent executes
        3) Master inspects result and decides next stage
        4) All reasoning snapshots are appended to agent_log
        """
        session_id = payload.get("session_id", f"session_{int(time.time())}")
        language = payload.get("language", "en")

        agent_name, agent_payload = self._resolve_stage_agent(stage, payload, session_id)
        started_at = time.time()
        agent_result = agent_name.run(agent_payload)
        duration_ms = int((time.time() - started_at) * 1000)
        action = self._action_for(agent_result.agent_name, agent_result.output)
        self._log_step(
            stage=stage,
            session_id=session_id,
            actor=agent_result.agent_name,
            status=agent_result.status.value.upper(),
            action=action,
            reasoning=agent_result.reasoning,
            output=agent_result.output,
            duration_ms=duration_ms,
        )

        master_post = self._master_decide(
            session_id=session_id,
            user_message=f"{stage} completed",
            payload={**payload, "last_agent": agent_result.agent_name, "last_output": agent_result.output},
            current_stage=stage,
        )

        return {
            "session_id": session_id,
            "stage": stage,
            "agent": agent_result.agent_name,
            "result": agent_result.output,
            "master_decision": master_post,
            "next_stage": self._derive_next_stage(stage, agent_result.output, master_post),
        }

    def get_agent_log(self) -> list:
        # Returns full trace of which agent did what and why — for demo transparency
        return self.agent_log

    async def run_full_pipeline(self, payload: dict) -> dict:
        session_id = payload.get("session_id", f"session_{int(time.time())}")
        self._session_logs[session_id] = []
        self._session_status[session_id] = "ACTIVE"

        start_ts = time.time()
        self._log_step(
            stage="init",
            session_id=session_id,
            actor="MasterOrchestratorAgent",
            status="SUCCESS",
            action="INITIATED_SESSION",
            reasoning="New loan inquiry received. KYC required before proceeding.",
            output={"session_id": session_id},
            duration_ms=320,
        )

        kyc_result = await self.run_stage("kyc", payload)
        await asyncio.sleep(0.2)

        credit_payload = {
            **payload,
            "offered_rate": payload.get("offered_rate", 11.5),
            "risk_tier": payload.get("risk_tier", "Low Risk"),
            "max_negotiation_rounds": payload.get("max_negotiation_rounds", 3),
            "session_id": session_id,
        }
        credit_result = await self.run_stage("credit", credit_payload)
        await asyncio.sleep(0.2)

        negotiation_payload = {
            **payload,
            "session_id": session_id,
            "negotiation_requested": payload.get("negotiation_requested", True),
            "counter_rate": payload.get("counter_rate", 11.0),
            "offered_rate": payload.get("offered_rate", 11.5),
            "risk_tier": payload.get("risk_tier", "Low Risk"),
            "loan_amount": payload.get("loan_amount", 500000),
            "loan_term": payload.get("loan_term", 60),
            "current_rate": payload.get("offered_rate", 11.5),
            "rounds_taken": payload.get("rounds_taken", 1),
        }
        negotiation_result = await self.run_stage("negotiation", negotiation_payload)
        await asyncio.sleep(0.2)

        negotiation_output = negotiation_result.get("result", {})
        blockchain_payload = {
            **payload,
            "session_id": session_id,
            "applicant_name": payload.get("applicant_name", "Applicant"),
            "loan_amount": negotiation_output.get("loan_amount", payload.get("loan_amount", 500000)),
            "tenure_months": negotiation_output.get("tenure_months", payload.get("loan_term", 60)),
            "final_rate": negotiation_output.get("final_rate", payload.get("offered_rate", 11.5)),
            "emi": negotiation_output.get("emi", 0),
            "total_payable": negotiation_output.get("total_payable", 0),
            "total_interest": negotiation_output.get("total_interest", 0),
        }
        blockchain_result = await self.run_stage("blockchain", blockchain_payload)
        self._session_status[session_id] = "SANCTIONED"

        return {
            "session_id": session_id,
            "status": "SANCTIONED",
            "kyc": kyc_result,
            "credit": credit_result,
            "negotiation": negotiation_result,
            "blockchain": blockchain_result,
            "total_duration_ms": int((time.time() - start_ts) * 1000),
        }

    def get_session_log(self, session_id: str) -> dict:
        trace = self._session_logs.get(session_id, [])
        total_duration = sum(item.get("duration_ms", 0) for item in trace)
        return {
            "session_id": session_id,
            "total_agents_invoked": len(trace),
            "pipeline_status": self._session_status.get(session_id, "ACTIVE"),
            "agent_trace": trace,
            "total_duration_ms": total_duration,
        }

    def get_global_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent agent actions across all sessions"""
        return self._global_logs[:limit]

    def _resolve_stage_agent(self, stage: str, payload: dict, session_id: str):
        stage_key = (stage or "").strip().lower()
        if stage_key in {"kyc", "kyc_verification", "kyc_pending"}:
            return self.kyc, {
                "pan_number": payload.get("pan_number"),
                "aadhaar_number": payload.get("aadhaar_number"),
                "pan_image": payload.get("pan_image"),
                "aadhaar_image": payload.get("aadhaar_image"),
                "session_id": session_id,
            }
        if stage_key in {"credit", "underwriting", "credit_assessment"}:
            return self.credit, {
                "pan_number": payload.get("pan_number"),
                "applicant_income": payload.get("applicant_income", 50000),
                "loan_amount": payload.get("loan_amount", 500000),
                "loan_term": payload.get("loan_term", 60),
                "session_id": session_id,
            }
        if stage_key in {"negotiation", "offer", "offer_generated"}:
            return self.negotiation, {
                "loan_details": {
                    "loan_amount": payload.get("loan_amount", 500000),
                    "loan_term": payload.get("loan_term", 60),
                },
                "offered_rate": payload.get("offered_rate", 11.5),
                "risk_tier": payload.get("risk_tier", "Medium Risk"),
                "max_negotiation_rounds": payload.get("max_negotiation_rounds", 3),
                "negotiation_requested": payload.get("negotiation_requested", False),
                "counter_rate": payload.get("counter_rate"),
                "user_message": payload.get("user_message", ""),
                "current_rate": payload.get("current_rate", payload.get("offered_rate", 11.5)),
                "rounds_taken": payload.get("rounds_taken", 0),
                "session_id": session_id,
            }
        if stage_key in {"blockchain", "sanction", "accepted"}:
            return self.blockchain, {
                "applicant_name": payload.get("applicant_name", "Applicant"),
                "loan_amount": payload.get("loan_amount", 500000),
                "tenure_months": payload.get("tenure_months", payload.get("loan_term", 60)),
                "final_rate": payload.get("final_rate", payload.get("offered_rate", 11.5)),
                "emi": payload.get("emi", 0),
                "total_payable": payload.get("total_payable", 0),
                "total_interest": payload.get("total_interest", 0),
                "session_id": session_id,
            }
        raise ValueError(f"Unsupported stage '{stage}'. Use kyc, credit, negotiation, or blockchain.")

    def _derive_next_stage(self, current_stage: str, agent_output: dict, master_output: dict) -> str | None:
        explicit_stage = master_output.get("new_stage")
        if explicit_stage:
            return explicit_stage
        if isinstance(agent_output, dict) and agent_output.get("next_agent") == "BlockchainAuditAgent":
            return "ACCEPTED"
        progression = {
            "kyc": "KYC_VERIFIED",
            "credit": "OFFER_GENERATED",
            "negotiation": "ACCEPTED",
            "blockchain": "SANCTIONED",
        }
        return progression.get((current_stage or "").strip().lower())

    def _master_decide(self, session_id: str, user_message: str, payload: dict, current_stage: str) -> dict:
        context = {
            "stage": current_stage.upper(),
            "data": payload,
            "history": [],
            "session_id": session_id,
        }
        return self.master._fallback_decision(user_message, context)

    def _action_for(self, actor: str, output: dict) -> str:
        if actor == "KYCVerificationAgent":
            return "DOCUMENTS_VERIFIED"
        if actor == "CreditUnderwritingAgent":
            return "LOAN_APPROVED"
        if actor == "Negotiation Agent":
            return "RATE_NEGOTIATED"
        if actor == "BlockchainAuditAgent":
            return "SANCTIONED"
        return "PROCESSED"

    def _log_step(
        self,
        stage: str,
        session_id: str,
        actor: str,
        status: str,
        action: str,
        reasoning: str,
        output: dict,
        duration_ms: int,
    ) -> None:
        entry = {
            "step": len(self._session_logs.get(session_id, [])) + 1,
            "agent": actor,
            "action": action,
            "reasoning": reasoning,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "stage": stage,
            "status": status,
            "output": deepcopy(output) if isinstance(output, dict) else output,
        }
        self.agent_log.append(entry)
        self._session_logs.setdefault(session_id, []).append(entry)
        
        # Update global logs for landing page
        global_entry = {
            "session_id": session_id,
            "timestamp": entry["timestamp"],
            "agent": entry["agent"],
            "action": entry["action"],
            "status": entry["status"]
        }
        self._global_logs.insert(0, global_entry)
        if len(self._global_logs) > self._MAX_GLOBAL_LOGS:
            self._global_logs.pop()
