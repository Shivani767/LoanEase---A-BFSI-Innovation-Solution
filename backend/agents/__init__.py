# LoanEase Agents Package
# Re-export all agent classes from the top-level agents.py module
import sys
import os
import importlib.util

# Load agents.py from the parent backend directory (one level up from this package)
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_agents_module_path = os.path.join(_backend_dir, "agents.py")

# Only load if not already cached
if "_agents_module" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("_agents_module", _agents_module_path)
    _agents_module = importlib.util.module_from_spec(_spec)
    # Register in sys.modules BEFORE exec so @dataclass and forward refs resolve correctly
    sys.modules["_agents_module"] = _agents_module
    _spec.loader.exec_module(_agents_module)
else:
    _agents_module = sys.modules["_agents_module"]

# Re-export all public names
AgentStatus = _agents_module.AgentStatus
AgentResult = _agents_module.AgentResult
Tool = _agents_module.Tool
BaseAgent = _agents_module.BaseAgent
KYCAgent = _agents_module.KYCAgent
UnderwritingAgent = _agents_module.UnderwritingAgent
KYCVerificationAgent = _agents_module.KYCVerificationAgent
NegotiationAgent = _agents_module.NegotiationAgent
BlockchainAuditAgent = _agents_module.BlockchainAuditAgent
CreditUnderwritingAgent = _agents_module.CreditUnderwritingAgent
TranslationAgent = _agents_module.TranslationAgent
OrchestratorAgent = _agents_module.OrchestratorAgent
ApplicationStage = _agents_module.ApplicationStage
MasterOrchestratorAgent = _agents_module.MasterOrchestratorAgent
LoanEaseOrchestrator = _agents_module.LoanEaseOrchestrator

__all__ = [
    "AgentStatus",
    "AgentResult",
    "Tool",
    "BaseAgent",
    "KYCAgent",
    "UnderwritingAgent",
    "KYCVerificationAgent",
    "NegotiationAgent",
    "BlockchainAuditAgent",
    "CreditUnderwritingAgent",
    "TranslationAgent",
    "OrchestratorAgent",
    "ApplicationStage",
    "MasterOrchestratorAgent",
    "LoanEaseOrchestrator",
]
