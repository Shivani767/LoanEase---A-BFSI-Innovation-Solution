"""
Demo script for LoanEase 5-Agent Orchestration System.

This script demonstrates:
1. How to initialize the orchestration system
2. How to run a complete workflow
3. How to access individual agents
4. How to interpret results

Run with: python demo_agents.py
"""

from agents import (
    LoanEaseOrchestrator,
    AgentResult,
    AgentStatus,
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(result: AgentResult):
    """Print agent result in a formatted way."""
    print(f"\n  Agent: {result.agent_name}")
    print(f"  Status: {result.status.value}")
    print(f"  Duration: {result.duration_ms}ms")
    print(f"  Reasoning: {result.reasoning}")
    if result.next_agent:
        print(f"  Next Agent: {result.next_agent}")


def demo_list_agents():
    """Demo: List all available agents."""
    print_section("DEMO 1: LIST ALL AGENTS")
    
    orchestrator = LoanEaseOrchestrator()
    agents = orchestrator.list_agents()
    
    for agent in agents:
        print(f"\n  📋 {agent['name']}")
        print(f"     Role: {agent['role']}")
        print(f"     Tools: {', '.join(agent['tools'])}")


def demo_kyc_agent():
    """Demo: Run KYC Agent independently."""
    print_section("DEMO 2: KYC AGENT (DOCUMENT VERIFICATION)")
    
    from agents import KYCAgent
    
    kyc = KYCAgent()
    input_data = {
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "session_id": "demo_kyc_001"
    }
    
    result = kyc.run(input_data)
    print_result(result)
    
    if result.status == AgentStatus.SUCCESS:
        print(f"\n  ✅ KYC Verified!")
        print(f"     PAN: {result.output['pan_details']['pan_number']}")
        print(f"     Name: {result.output['pan_details']['name']}")
        print(f"     Eligible: {result.output['eligibility']['eligible']}")


def demo_underwriting_agent():
    """Demo: Run Underwriting Agent independently."""
    print_section("DEMO 3: UNDERWRITING AGENT (CREDIT ASSESSMENT)")
    
    from agents import UnderwritingAgent
    
    uw = UnderwritingAgent()
    input_data = {
        "pan_details": {"pan_number": "ABCDE1234F"},
        "applicant_income": 75000,
        "loan_amount": 1000000,
        "loan_term": 48,
        "session_id": "demo_uw_001"
    }
    
    result = uw.run(input_data)
    print_result(result)
    
    if result.status == AgentStatus.SUCCESS:
        print(f"\n  ✅ Assessment Complete!")
        print(f"     Decision: {result.output['decision']}")
        print(f"     Credit Score: {result.output['credit_score']}")
        print(f"     Risk Tier: {result.output['risk_tier']}")
        print(f"     Offered Rate: {result.output['offered_rate']}% p.a.")
        print(f"     Monthly EMI: ₹{result.output['loan_details']['monthly_emi']:,.2f}")


def demo_negotiation_agent():
    """Demo: Run Negotiation Agent."""
    print_section("DEMO 4: NEGOTIATION AGENT (RATE NEGOTIATION)")
    
    from agents import NegotiationAgent
    
    neg = NegotiationAgent()
    input_data = {
        "loan_details": {"loan_amount": 500000, "loan_term": 36},
        "offered_rate": 10.5,
        "risk_tier": "Low Risk",
        "max_negotiation_rounds": 3,
        "negotiation_requested": True,
        "counter_rate": 9.5,
        "session_id": "demo_neg_001"
    }
    
    result = neg.run(input_data)
    print_result(result)
    
    if result.status == AgentStatus.SUCCESS:
        print(f"\n  ✅ Negotiation Complete!")
        print(f"     Initial Rate: {result.output['initial_rate']}%")
        print(f"     Final Rate: {result.output['final_rate']}%")
        print(f"     Monthly EMI: ₹{result.output['monthly_emi']:,.2f}")
        print(f"     Total Payable: ₹{result.output['total_payable']:,.2f}")


def demo_translation_agent():
    """Demo: Run Translation Agent."""
    print_section("DEMO 5: TRANSLATION AGENT (MULTILINGUAL SUPPORT)")
    
    from agents import TranslationAgent
    
    trans = TranslationAgent()
    input_data = {
        "text_to_translate": "Your loan application has been approved",
        "source_language": "en",
        "target_language": "hi",
        "session_id": "demo_trans_001"
    }
    
    result = trans.run(input_data)
    print_result(result)
    
    if result.status == AgentStatus.SUCCESS:
        print(f"\n  ✅ Translation Complete!")
        print(f"     Original: {result.output['translation']['original_text']}")
        print(f"     Translated: {result.output['translation']['translated_text']}")


def demo_complete_workflow():
    """Demo: Run complete orchestration workflow."""
    print_section("DEMO 6: COMPLETE ORCHESTRATION WORKFLOW")
    
    orchestrator = LoanEaseOrchestrator()
    
    # Complete application data
    application_data = {
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "applicant_income": 75000,
        "loan_amount": 1000000,
        "loan_term": 48,
        "preferred_language": "en",
        "negotiation_requested": False,
    }
    
    print("\n  Submitting loan application...")
    print(f"     PAN: {application_data['pan_number']}")
    print(f"     Loan Amount: ₹{application_data['loan_amount']:,.0f}")
    print(f"     Tenure: {application_data['loan_term']} months")
    
    result = orchestrator.run_workflow(application_data)
    
    print(f"\n  📊 Workflow Result:")
    print(f"     Status: {result.status.value}")
    print(f"     Total Duration: {result.duration_ms}ms")
    
    # Show workflow history
    history = result.output.get("workflow_history", [])
    print(f"\n  🔄 Agents Executed:")
    for i, step in enumerate(history, 1):
        print(f"     {i}. {step['agent_name']} - {step['status']}")
    
    # Show application summary
    summary = result.output.get("application_summary", {})
    print(f"\n  📋 Application Summary:")
    for key, value in summary.items():
        print(f"     {key}: {value}")
    
    # Show next steps
    next_steps = result.output.get("next_steps", [])
    print(f"\n  📝 Next Steps:")
    for step in next_steps:
        print(f"     • {step}")


def demo_workflow_with_negotiation():
    """Demo: Workflow with negotiation."""
    print_section("DEMO 7: WORKFLOW WITH NEGOTIATION")
    
    orchestrator = LoanEaseOrchestrator()
    
    application_data = {
        "pan_number": "XYZPQ5678K",
        "aadhaar_number": "987654321098",
        "applicant_income": 60000,
        "loan_amount": 750000,
        "loan_term": 36,
        "preferred_language": "hi",
        "negotiation_requested": True,
        "counter_rate": 9.0,
    }
    
    print("\n  Submitting loan application with negotiation...")
    
    result = orchestrator.run_workflow(application_data)
    
    print(f"\n  📊 Workflow Result:")
    print(f"     Status: {result.status.value}")
    print(f"     Reasoning: {result.reasoning}")
    
    summary = result.output.get("application_summary", {})
    print(f"\n  📋 Final Offer:")
    print(f"     Decision: {summary.get('decision')}")
    print(f"     Credit Score: {summary.get('credit_score')}")
    print(f"     Final Rate: {summary.get('final_rate')}% p.a.")
    print(f"     Monthly EMI: ₹{summary.get('monthly_emi'):,.2f}")


def main():
    """Run all demos."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         LOANEASE 5-AGENT ORCHESTRATION SYSTEM DEMO                  ║
║                                                                      ║
║         A lightweight custom agent framework (no LangChain)         ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Run demos
    demo_list_agents()
    demo_kyc_agent()
    demo_underwriting_agent()
    demo_negotiation_agent()
    demo_translation_agent()
    demo_complete_workflow()
    demo_workflow_with_negotiation()
    
    print("\n" + "=" * 70)
    print("  ALL DEMOS COMPLETED!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()