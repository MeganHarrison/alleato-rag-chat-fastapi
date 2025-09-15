"""Financial analysis tools for construction project cost management."""

from typing import Optional, List, Dict, Any, Union
from pydantic_ai import RunContext
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
from shared.ai.agent_deps import AgentDeps

try:
    from shared.monitoring.tracing import get_tracer
    ADVANCED_TRACING = True
except ImportError:
    from shared.monitoring.simple_tracing import get_simple_tracer as get_tracer
    ADVANCED_TRACING = False


class BudgetVarianceResult(BaseModel):
    """Model for budget variance analysis results."""
    project_name: str
    original_budget: float
    actual_spending: float
    variance_amount: float
    variance_percentage: float
    status: str  # "over_budget", "under_budget", "on_budget"
    risk_level: str  # "low", "moderate", "high", "critical"
    analysis: str


class TimelineCostImpact(BaseModel):
    """Model for timeline delay cost calculations."""
    project_name: str
    delay_days: int
    daily_overhead_cost: float
    total_delay_cost: float
    labor_impact: float
    equipment_impact: float
    opportunity_cost: float
    analysis: str


@get_tracer().trace_search_operation("budget_variance")
async def calculate_budget_variance(
    ctx: RunContext[AgentDeps],
    project_name: str,
    original_budget: float,
    actual_spending: float,
    completion_percentage: Optional[float] = None
) -> BudgetVarianceResult:
    """
    Calculate budget variance and provide veteran PM analysis.
    
    Use this when discussing project financials, cost overruns, or budget status.
    
    Args:
        ctx: Agent runtime context
        project_name: Name of the project
        original_budget: Original approved budget
        actual_spending: Current actual spending
        completion_percentage: Optional % complete (for burn rate analysis)
    
    Returns:
        Detailed budget variance analysis with PM insights
    """
    
    # Calculate variance
    variance_amount = actual_spending - original_budget
    variance_percentage = (variance_amount / original_budget) * 100 if original_budget > 0 else 0
    
    # Determine status
    if abs(variance_percentage) <= 2:
        status = "on_budget"
    elif variance_percentage > 0:
        status = "over_budget"
    else:
        status = "under_budget"
    
    # Determine risk level
    if abs(variance_percentage) <= 5:
        risk_level = "low"
    elif abs(variance_percentage) <= 15:
        risk_level = "moderate"
    elif abs(variance_percentage) <= 25:
        risk_level = "high"
    else:
        risk_level = "critical"
    
    # Generate veteran PM analysis
    if status == "over_budget":
        if variance_percentage <= 10:
            analysis = f"We're running {variance_percentage:.1f}% over on {project_name}. Not catastrophic, but we need to tighten the screws. This usually means scope creep or change orders nobody wants to talk about."
        elif variance_percentage <= 25:
            analysis = f"Alright, {project_name} is bleeding money - {variance_percentage:.1f}% over budget. Time for an uncomfortable conversation with someone. Check for undocumented changes, permit delays causing labor overruns, or material cost surprises."
        else:
            analysis = f"Houston, we have a problem. {project_name} is {variance_percentage:.1f}% over budget - that's ${variance_amount:,.0f} in the hole. This isn't a budget variance anymore, it's a financial disaster. Emergency meeting required."
    
    elif status == "under_budget":
        if completion_percentage and completion_percentage < 80:
            analysis = f"{project_name} shows {abs(variance_percentage):.1f}% under budget, but hold your horses - we're probably just not billing fast enough or materials haven't hit yet. Don't celebrate until we're at 90% completion."
        else:
            analysis = f"Good news for once - {project_name} came in {abs(variance_percentage):.1f}% under budget. Either we estimated conservatively or someone actually managed the scope properly. I'll take it."
    
    else:
        analysis = f"{project_name} is remarkably close to budget - {variance_percentage:.1f}% variance. Either the estimating team nailed it or we're missing some bills. Keep watching this one."
    
    # Add completion percentage context
    if completion_percentage:
        if completion_percentage < 50 and variance_percentage > 10:
            analysis += f" At {completion_percentage:.0f}% complete, this trajectory is ugly. Projected final overrun could hit {variance_percentage * 2:.1f}%."
        elif completion_percentage > 80 and status == "over_budget":
            analysis += f" At {completion_percentage:.0f}% complete, the damage is mostly done. Focus on controlling the final 20%."
    
    return BudgetVarianceResult(
        project_name=project_name,
        original_budget=original_budget,
        actual_spending=actual_spending,
        variance_amount=variance_amount,
        variance_percentage=variance_percentage,
        status=status,
        risk_level=risk_level,
        analysis=analysis
    )


@get_tracer().trace_search_operation("timeline_cost")
async def calculate_timeline_cost_impact(
    ctx: RunContext[AgentDeps],
    project_name: str,
    delay_days: int,
    daily_overhead_cost: Optional[float] = None,
    project_value: Optional[float] = None,
    crew_size: Optional[int] = None
) -> TimelineCostImpact:
    """
    Calculate the financial impact of project delays.
    
    Use this for timeline discussions, delay analysis, and cost projections.
    
    Args:
        ctx: Agent runtime context
        project_name: Name of the project
        delay_days: Number of delay days
        daily_overhead_cost: Optional daily overhead (estimated if not provided)
        project_value: Optional total project value for percentage calculations
        crew_size: Optional crew size for labor calculations
    
    Returns:
        Detailed timeline cost impact analysis
    """
    
    # Estimate daily overhead if not provided
    if not daily_overhead_cost:
        if project_value:
            # Rough estimate: 0.1-0.3% of project value per day
            daily_overhead_cost = project_value * 0.002
        else:
            # Default estimate for construction projects
            daily_overhead_cost = 2500
    
    # Calculate labor impact
    if crew_size:
        # Assume average $35/hour * 8 hours * crew size
        labor_impact = crew_size * 35 * 8 * delay_days
    else:
        # Estimate based on overhead
        labor_impact = daily_overhead_cost * 0.6 * delay_days
    
    # Calculate equipment impact (typically 20-30% of overhead)
    equipment_impact = daily_overhead_cost * 0.25 * delay_days
    
    # Calculate opportunity cost (lost revenue from next project)
    if project_value:
        # Assume 12% annual margin, calculate daily opportunity cost
        opportunity_cost = (project_value * 0.12 / 365) * delay_days
    else:
        opportunity_cost = daily_overhead_cost * 0.15 * delay_days
    
    # Total delay cost
    total_delay_cost = daily_overhead_cost * delay_days + labor_impact + equipment_impact + opportunity_cost
    
    # Generate veteran PM analysis
    if delay_days <= 3:
        severity = "minor hiccup"
        impact_desc = "annoying but manageable"
    elif delay_days <= 10:
        severity = "real problem"
        impact_desc = "starting to hurt the bottom line"
    elif delay_days <= 20:
        severity = "serious issue"
        impact_desc = "bleeding money daily"
    else:
        severity = "disaster"
        impact_desc = "financial catastrophe in progress"
    
    analysis = f"{project_name} is facing a {delay_days}-day delay - that's a {severity}. "
    analysis += f"We're looking at ${total_delay_cost:,.0f} in delay costs, which is {impact_desc}. "
    
    if delay_days > 7:
        analysis += f"At ${daily_overhead_cost:,.0f} per day in overhead alone, plus labor and opportunity costs, "
        analysis += "we need to get aggressive about removing bottlenecks. "
    
    # Add context based on cause
    analysis += "This assumes the delay is real - sometimes 'delays' are just poor scheduling or wishful thinking. "
    analysis += "But if it's permits, weather, or material shortages, then yeah, we're stuck and the clock is ticking."
    
    if project_value:
        percentage_impact = (total_delay_cost / project_value) * 100
        analysis += f" That's {percentage_impact:.1f}% of the total project value - ouch."
    
    return TimelineCostImpact(
        project_name=project_name,
        delay_days=delay_days,
        daily_overhead_cost=daily_overhead_cost,
        total_delay_cost=total_delay_cost,
        labor_impact=labor_impact,
        equipment_impact=equipment_impact,
        opportunity_cost=opportunity_cost,
        analysis=analysis
    )


@get_tracer().trace_search_operation("cost_projection")
async def project_final_cost(
    ctx: RunContext[AgentDeps],
    project_name: str,
    original_budget: float,
    actual_spending: float,
    completion_percentage: float,
    remaining_risks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Project final costs based on current spending patterns and remaining risks.
    
    Args:
        ctx: Agent runtime context
        project_name: Name of the project
        original_budget: Original approved budget
        actual_spending: Current actual spending
        completion_percentage: Percentage complete (0-100)
        remaining_risks: List of remaining risk factors
    
    Returns:
        Cost projection analysis with scenarios
    """
    
    if completion_percentage <= 0:
        completion_percentage = 1  # Avoid division by zero
    
    # Calculate current burn rate
    burn_rate = actual_spending / (completion_percentage / 100)
    projected_final_cost = burn_rate
    
    # Calculate scenarios
    best_case = projected_final_cost * 0.95  # Assuming some efficiency gains
    worst_case = projected_final_cost * 1.15  # Assuming typical overruns
    
    # Adjust for remaining risks
    risk_multiplier = 1.0
    if remaining_risks:
        risk_factors = {
            "permit": 0.05,
            "weather": 0.03,
            "inspection": 0.04,
            "material": 0.08,
            "labor": 0.06,
            "change order": 0.10,
            "fire marshal": 0.06
        }
        
        for risk in remaining_risks:
            for factor, multiplier in risk_factors.items():
                if factor.lower() in risk.lower():
                    risk_multiplier += multiplier
                    break
    
    realistic_final_cost = projected_final_cost * risk_multiplier
    
    # Generate analysis
    variance_amount = realistic_final_cost - original_budget
    variance_percentage = (variance_amount / original_budget) * 100
    
    if variance_percentage <= 5:
        outlook = "Pretty solid"
        advice = "Keep doing whatever you're doing"
    elif variance_percentage <= 15:
        outlook = "Manageable but watch it"
        advice = "Time to get serious about cost control"
    elif variance_percentage <= 25:
        outlook = "Problem territory" 
        advice = "Emergency cost-cutting measures needed"
    else:
        outlook = "Financial disaster zone"
        advice = "Stop everything and figure out what went wrong"
    
    analysis = f"{outlook} - {project_name} is projecting ${realistic_final_cost:,.0f} final cost "
    analysis += f"({variance_percentage:+.1f}% vs original budget). {advice}. "
    
    if completion_percentage < 75:
        analysis += f"At {completion_percentage:.0f}% complete, there's still time to course-correct if we act fast."
    else:
        analysis += f"At {completion_percentage:.0f}% complete, most damage is done. Focus on controlling the finish."
    
    return {
        "project_name": project_name,
        "completion_percentage": completion_percentage,
        "projected_final_cost": realistic_final_cost,
        "best_case_cost": best_case,
        "worst_case_cost": worst_case,
        "variance_amount": variance_amount,
        "variance_percentage": variance_percentage,
        "risk_factors": remaining_risks or [],
        "analysis": analysis,
        "scenarios": {
            "best_case": best_case,
            "realistic": realistic_final_cost,
            "worst_case": worst_case * risk_multiplier
        }
    }