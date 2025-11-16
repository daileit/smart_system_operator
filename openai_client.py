"""
OpenAI client module for Smart System Operator.
Provides AI-powered decision making for server actions based on metrics and logs.
"""

import jsonlog
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from openai import OpenAI
import config as env_config

logger = jsonlog.setup_logger("openai_client")


@dataclass
class AIDecision:
    """AI decision result for server actions."""
    recommended_actions: List[Dict[str, Any]]
    reasoning: str
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    requires_approval: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AIDecision to dictionary."""
        return {
            'recommended_actions': self.recommended_actions,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'requires_approval': self.requires_approval
        }


class OpenAIClient:
    """OpenAI client for AI-powered server management decisions."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to env config)
            model: Model to use (defaults to env config or gpt-4o)
        """
        self.api_key = api_key or env_config.Config(group="OPENAI").get("API_KEY")
        self.model = model or env_config.Config(group="OPENAI").get("MODEL", "gpt-4o")
        
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.logger = logger
    
    @staticmethod
    def fetch_available_models(api_key: Optional[str] = None) -> List[Tuple[str, str, bool, int]]:
        """
        Fetch available models from OpenAI API.
        
        Args:
            api_key: OpenAI API key (defaults to env config)
            
        Returns:
            List of tuples: (model_id, label, is_default, display_order)
        """
        try:
            if not api_key:
                openai_config = env_config.Config(group="OPENAI")
                api_key = openai_config.get("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("OPENAI_API_KEY not configured, using fallback model list")
                return [
                    ('gpt-4o-mini', 'GPT-4o Mini (OpenAI)', True, 1),
                    ('gpt-4o', 'GPT-4o (OpenAI)', False, 2),
                ]
            
            client = OpenAI(api_key=api_key)
            models_response = client.models.list()
            
            # Filter for GPT models only (exclude embedding, tts, whisper, etc.)
            gpt_models = []
            display_order = 1
            
            for model in models_response.data:
                model_id = model.id
                # Include only GPT chat models
                if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5']):
                    # Set gpt-4o-mini as default
                    is_default = model_id == 'gpt-4o-mini'
                    
                    # Create friendly label
                    label = model_id.upper().replace('-', ' ').replace('_', ' ')
                    label = f"{label} (OpenAI)"
                    
                    gpt_models.append((model_id, label, is_default, display_order))
                    display_order += 1
            
            # Sort by model name (gpt-4 first, then gpt-3.5)
            gpt_models.sort(key=lambda x: (0 if 'gpt-4' in x[0] else 1, x[0]))
            
            # Re-assign display order after sorting
            gpt_models = [(m[0], m[1], m[2], i+1) for i, m in enumerate(gpt_models)]
            
            if not gpt_models:
                logger.warning("No GPT models found, using fallback model list")
                return [
                    ('gpt-4o-mini', 'GPT-4o Mini (OpenAI)', True, 1),
                    ('gpt-4o', 'GPT-4o (OpenAI)', False, 2),
                ]
            
            logger.info(f"Fetched {len(gpt_models)} available OpenAI models")
            return gpt_models
            
        except Exception as e:
            logger.error(f"Error fetching OpenAI models: {e}")
            logger.warning("Using fallback model list")
            return [
                ('gpt-4o-mini', 'GPT-4o Mini (OpenAI)', True, 1),
                ('gpt-4o', 'GPT-4o (OpenAI)', False, 2),
            ]
        
        # System prompt for server management AI
        self.system_prompt = """You are an expert server operations AI assistant for the Smart System Operator platform.

Your role is to analyze server metrics, execution logs, and system status to recommend appropriate actions.

IMPORTANT GUIDELINES:
1. SAFETY FIRST: Never recommend high-risk actions (reboot, stop services) unless absolutely necessary
2. EXPLAIN REASONING: Always provide clear, detailed reasoning for your recommendations
3. CONFIDENCE LEVELS: Be honest about uncertainty - use confidence scores appropriately
4. RISK ASSESSMENT: Classify every recommendation as low/medium/high risk
5. APPROVAL REQUIREMENTS: High-risk actions should always require human approval

AVAILABLE ACTION TYPES:
- command_execute: Modify server state (HIGH RISK - reboot, stop/start services, kill processes, etc.)
- command_get: Gather information (LOW RISK - check status, get metrics, list processes, etc.)
- http: Make HTTP API calls (MEDIUM RISK - depends on endpoint)

DECISION FRAMEWORK:
1. Analyze the current server metrics and logs
2. Identify potential issues or anomalies
3. Recommend the least invasive actions first (prefer command_get over command_execute)
4. Only recommend execute actions if monitoring shows clear problems
5. Always explain what you're trying to achieve and why

OUTPUT FORMAT:
Return a JSON object with:
{
    "recommended_actions": [
        {
            "action_id": <int>,
            "action_name": "<string>",
            "priority": <int 1-10>,
            "parameters": {<param_name>: <param_value>},
            "reasoning": "<why this action>"
        }
    ],
    "reasoning": "<overall reasoning>",
    "confidence": <float 0.0-1.0>,
    "risk_level": "<low|medium|high>",
    "requires_approval": <boolean>
}"""
    
    def analyze_server_metrics(self, 
                               server_info: Dict[str, Any],
                               available_actions: List[Dict[str, Any]],
                               execution_logs: Optional[List[Dict[str, Any]]] = None,
                               server_statistics: Optional[Dict[str, Any]] = None,
                               current_metrics: Optional[Dict[str, Any]] = None) -> AIDecision:
        """
        Analyze server metrics and recommend actions.
        
        Args:
            server_info: Server details (name, ip, description, etc.)
            available_actions: List of actions available for this server
            execution_logs: Recent execution logs
            server_statistics: Server execution statistics
            current_metrics: Current server metrics (CPU, memory, disk, etc.)
            
        Returns:
            AIDecision with recommended actions and reasoning
        """
        try:
            # Build context for AI
            context = self._build_context(
                server_info, 
                available_actions, 
                execution_logs, 
                server_statistics,
                current_metrics
            )
            
            # Create user message
            user_message = f"""Analyze this server and recommend appropriate actions:

SERVER INFORMATION:
{json.dumps(server_info, indent=2, default=str)}

AVAILABLE ACTIONS:
{json.dumps(available_actions, indent=2, default=str)}

RECENT EXECUTION LOGS (last 10):
{json.dumps(execution_logs or [], indent=2, default=str)}

SERVER STATISTICS:
{json.dumps(server_statistics or {}, indent=2, default=str)}

CURRENT METRICS:
{json.dumps(current_metrics or {}, indent=2, default=str)}

Based on this information, recommend the most appropriate actions to take. Focus on monitoring first, only suggest interventions if there are clear issues."""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Lower temperature for more consistent decisions
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Create AIDecision object
            decision = AIDecision(
                recommended_actions=result.get('recommended_actions', []),
                reasoning=result.get('reasoning', ''),
                confidence=result.get('confidence', 0.0),
                risk_level=result.get('risk_level', 'medium'),
                requires_approval=result.get('requires_approval', True)
            )
            
            self.logger.info(f"AI analysis completed for server {server_info.get('name')}: "
                           f"{len(decision.recommended_actions)} actions recommended")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis: {e}")
            # Return safe default decision
            return AIDecision(
                recommended_actions=[],
                reasoning=f"Error during AI analysis: {str(e)}",
                confidence=0.0,
                risk_level='high',
                requires_approval=True
            )
    
    def analyze_specific_issue(self,
                              server_info: Dict[str, Any],
                              issue_description: str,
                              available_actions: List[Dict[str, Any]],
                              execution_logs: Optional[List[Dict[str, Any]]] = None) -> AIDecision:
        """
        Analyze a specific reported issue and recommend actions.
        
        Args:
            server_info: Server details
            issue_description: Description of the issue to address
            available_actions: List of available actions
            execution_logs: Recent execution logs for context
            
        Returns:
            AIDecision with recommended actions
        """
        try:
            user_message = f"""A specific issue has been reported for this server:

ISSUE: {issue_description}

SERVER: {server_info.get('name')} ({server_info.get('ip_address')})

AVAILABLE ACTIONS:
{json.dumps(available_actions, indent=2, default=str)}

RECENT LOGS:
{json.dumps(execution_logs or [], indent=2, default=str)}

Recommend actions to address this specific issue. Be specific about parameters needed for each action."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            decision = AIDecision(
                recommended_actions=result.get('recommended_actions', []),
                reasoning=result.get('reasoning', ''),
                confidence=result.get('confidence', 0.0),
                risk_level=result.get('risk_level', 'medium'),
                requires_approval=result.get('requires_approval', True)
            )
            
            self.logger.info(f"AI issue analysis completed: {len(decision.recommended_actions)} actions recommended")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in issue analysis: {e}")
            return AIDecision(
                recommended_actions=[],
                reasoning=f"Error during issue analysis: {str(e)}",
                confidence=0.0,
                risk_level='high',
                requires_approval=True
            )
    
    def validate_action(self,
                       server_info: Dict[str, Any],
                       action_info: Dict[str, Any],
                       parameters: Dict[str, str],
                       execution_logs: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str, str]:
        """
        Validate if an action is safe and appropriate to execute.
        
        Args:
            server_info: Server details
            action_info: Action to validate
            parameters: Parameters for the action
            execution_logs: Recent execution logs
            
        Returns:
            Tuple of (is_safe, risk_level, reasoning)
        """
        try:
            user_message = f"""Validate if this action is safe to execute:

SERVER: {server_info.get('name')} ({server_info.get('ip_address')})

ACTION: {action_info.get('action_name')}
TYPE: {action_info.get('action_type')}
DESCRIPTION: {action_info.get('description')}
COMMAND: {action_info.get('command_template', 'N/A')}

PARAMETERS: {json.dumps(parameters, indent=2)}

RECENT EXECUTION HISTORY:
{json.dumps(execution_logs or [], indent=2, default=str)}

Assess if this action is safe to execute now. Return JSON with:
{{
    "is_safe": <boolean>,
    "risk_level": "<low|medium|high>",
    "reasoning": "<detailed explanation>",
    "warnings": ["<warning1>", "<warning2>"],
    "prerequisites": ["<check1>", "<check2>"]
}}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            is_safe = result.get('is_safe', False)
            risk_level = result.get('risk_level', 'high')
            reasoning = result.get('reasoning', '')
            warnings = result.get('warnings', [])
            
            full_reasoning = reasoning
            if warnings:
                full_reasoning += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)
            
            self.logger.info(f"Action validation: {action_info.get('action_name')} - "
                           f"Safe: {is_safe}, Risk: {risk_level}")
            
            return is_safe, risk_level, full_reasoning
            
        except Exception as e:
            self.logger.error(f"Error in action validation: {e}")
            return False, 'high', f"Error during validation: {str(e)}"
    
    def explain_execution_result(self,
                                server_info: Dict[str, Any],
                                action_info: Dict[str, Any],
                                execution_result: str,
                                was_successful: bool) -> str:
        """
        Explain an action execution result in human-readable terms.
        
        Args:
            server_info: Server details
            action_info: Action that was executed
            execution_result: Raw output from execution
            was_successful: Whether execution succeeded
            
        Returns:
            Human-readable explanation
        """
        try:
            user_message = f"""Explain this execution result in clear, concise terms:

SERVER: {server_info.get('name')}
ACTION: {action_info.get('action_name')}
SUCCESS: {was_successful}

EXECUTION OUTPUT:
{execution_result}

Provide a brief, clear explanation of what happened and what it means. 
Focus on actionable insights. If there are any warnings or issues, highlight them."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful server operations assistant. "
                                                 "Explain technical output in clear, concise terms."},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            explanation = response.choices[0].message.content.strip()
            
            self.logger.info(f"Generated explanation for {action_info.get('action_name')}")
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Error generating explanation: {e}")
            return f"Execution {'succeeded' if was_successful else 'failed'}. Raw output: {execution_result[:200]}"
    
    def suggest_monitoring_strategy(self,
                                   server_info: Dict[str, Any],
                                   available_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Suggest a monitoring strategy for a server.
        
        Args:
            server_info: Server details
            available_actions: Available actions for monitoring
            
        Returns:
            Monitoring strategy with recommended actions and schedules
        """
        try:
            # Filter to only get monitoring actions
            monitoring_actions = [a for a in available_actions if a.get('action_type') == 'command_get']
            
            user_message = f"""Design a monitoring strategy for this server:

SERVER: {server_info.get('name')} ({server_info.get('ip_address')})
DESCRIPTION: {server_info.get('description', 'N/A')}

AVAILABLE MONITORING ACTIONS:
{json.dumps(monitoring_actions, indent=2, default=str)}

Recommend which monitoring actions to run and how frequently. Return JSON with:
{{
    "monitoring_actions": [
        {{
            "action_id": <int>,
            "action_name": "<string>",
            "frequency": "<every_5min|every_15min|every_hour|daily>",
            "priority": <int 1-10>,
            "reasoning": "<why this check>"
        }}
    ],
    "reasoning": "<overall strategy explanation>"
}}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"Generated monitoring strategy for {server_info.get('name')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating monitoring strategy: {e}")
            return {
                'monitoring_actions': [],
                'reasoning': f"Error generating strategy: {str(e)}"
            }
    
    def _build_context(self,
                      server_info: Dict[str, Any],
                      available_actions: List[Dict[str, Any]],
                      execution_logs: Optional[List[Dict[str, Any]]],
                      server_statistics: Optional[Dict[str, Any]],
                      current_metrics: Optional[Dict[str, Any]]) -> str:
        """Build context string for AI analysis."""
        context_parts = [
            f"Server: {server_info.get('name')} ({server_info.get('ip_address')}:{server_info.get('port')})"
        ]
        
        if server_info.get('description'):
            context_parts.append(f"Description: {server_info.get('description')}")
        
        if server_statistics:
            context_parts.append(f"Total executions: {server_statistics.get('total_executions', 0)}")
            context_parts.append(f"Success rate: {server_statistics.get('success_count', 0)}/{server_statistics.get('total_executions', 0)}")
        
        if execution_logs:
            recent_failures = [log for log in execution_logs if log.get('status') == 'failed']
            if recent_failures:
                context_parts.append(f"Recent failures: {len(recent_failures)}")
        
        return " | ".join(context_parts)
    
    def chat_about_server(self,
                         server_info: Dict[str, Any],
                         user_question: str,
                         execution_logs: Optional[List[Dict[str, Any]]] = None,
                         conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Chat interface for asking questions about a server.
        
        Args:
            server_info: Server details
            user_question: User's question
            execution_logs: Recent execution logs for context
            conversation_history: Previous messages in conversation
            
        Returns:
            AI response
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt + 
                 "\n\nYou are now in conversational mode. Answer the user's questions about the server "
                 "based on available data. Be helpful, concise, and accurate."}
            ]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Build context message
            context = f"""Current server context:

SERVER: {server_info.get('name')} ({server_info.get('ip_address')})
DESCRIPTION: {server_info.get('description', 'N/A')}

RECENT LOGS:
{json.dumps(execution_logs or [], indent=2, default=str)}

USER QUESTION: {user_question}"""
            
            messages.append({"role": "user", "content": context})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            self.logger.info(f"Chat response generated for question about {server_info.get('name')}")
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
