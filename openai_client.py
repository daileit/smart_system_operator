"""
OpenAI client module for Smart System Operator.
Provides AI-powered decision making for server actions based on metrics and logs.
"""

import jsonlog
import json
import random
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from openai import OpenAI
import config as env_config
from redis_cache import RedisClient

logger = jsonlog.setup_logger("openai_client")


@dataclass
class AIDecision:
    """AI decision result for server actions."""
    recommended_actions: List[Dict[str, Any]]
    reasoning: str
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    requires_approval: bool
    model: str  # Model used for this analysis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AIDecision to dictionary."""
        return {
            'recommended_actions': self.recommended_actions,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'requires_approval': self.requires_approval,
            'model': self.model
        }


class OpenAIClient:
    """OpenAI client for AI-powered server management decisions."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to env config)
            model: Model(s) to use - can be a single model or comma-separated list for random selection
                   (defaults to env config or gpt-4o)
            base_url: API base URL (defaults to env config or https://api.openai.com/v1)
        """
        openai_config = env_config.Config(group="OPENAI")
        
        self.api_key = api_key or openai_config.get("OPENAI_API_KEY")
        self.model_config = model or openai_config.get("OPENAI_MODEL", "gpt-4o")
        self.base_url = base_url or openai_config.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OpenAI API key is required")
        
        # Parse model configuration - support comma-separated list for random selection
        self.model_list = [m.strip() for m in self.model_config.split(',') if m.strip()]
        if not self.model_list:
            self.model_list = ["gpt-4o"]
        
        # Initialize client with base_url support
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.logger = logger
        
        # Initialize Redis client for model ignore cache
        try:
            self.redis = RedisClient()
        except Exception as e:
            self.logger.warning(f"Redis client initialization failed: {e}. Model ignore cache disabled.")
            self.redis = None
        
        # Initialize system prompt
        self._init_system_prompt()
        
        if len(self.model_list) > 1:
            logger.info(f"OpenAI client initialized with base_url: {self.base_url}, "
                       f"models: {self.model_list} (random selection enabled)")
        else:
            logger.info(f"OpenAI client initialized with base_url: {self.base_url}, "
                       f"model: {self.model_list[0]}")
    
    def _get_model(self, ignore_model: str = "") -> str:
        """
        Get a model to use for the current request.        
        Args:
            ignore_model: Model name to ignore and cache for 2 hours (7200s)        
        Returns:
            Model name to use
        """
        if ignore_model and self.redis:
            ignore_key = f"smart_system:ignored_model:{ignore_model}"
            try:
                self.redis.set_string(ignore_key, "1", ttl=7200)
                self.logger.info(f"Cached ignored model: {ignore_model} (TTL: 7200s)")
            except Exception as e:
                self.logger.warning(f"Failed to cache ignored model {ignore_model}: {e}")
        
        if len(self.model_list) == 1:
            return self.model_list[0]
        
        max_attempts = len(self.model_list)
        
        for attempt in range(max_attempts):
            selected_model = random.choice(self.model_list)            
            if self.redis:
                ignore_key = f"smart_system:ignored_model:{selected_model}"
                try:
                    if self.redis.exists(ignore_key):
                        self.logger.debug(f"Model {selected_model} is ignored, retrying... (attempt {attempt + 1}/{max_attempts})")
                        continue
                except Exception as e:
                    self.logger.warning(f"Failed to check ignore cache for {selected_model}: {e}")

            self.logger.debug(f"Selected model: {selected_model} from {self.model_list}")
            return selected_model

        selected_model = random.choice(self.model_list)
        self.logger.warning(f"All models are ignored. Returning random model anyway: {selected_model}")
        return selected_model
    
    @staticmethod
    def fetch_available_models(api_key: Optional[str] = None, base_url: Optional[str] = None) -> List[Tuple[str, str, bool, int]]:
        """
        Fetch available models from OpenAI-compatible API endpoint.
        
        Args:
            api_key: API key (defaults to env config)
            base_url: API base URL (defaults to env config)
            
        Returns:
            List of tuples: (model_id, label, is_default, display_order)
        """
        try:
            openai_config = env_config.Config(group="OPENAI")
            
            if not api_key:
                api_key = openai_config.get("OPENAI_API_KEY")
            
            if not base_url:
                base_url = openai_config.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            
            if not api_key:
                logger.error("OPENAI_API_KEY not configured")
                return None
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            models_response = client.models.list()
            
            default_model_config = openai_config.get("OPENAI_MODEL", "gpt-4o")
            default_model_list = [m.strip() for m in default_model_config.split(',') if m.strip()]
            

            available_models = []
            display_order = 1
            
            for model in models_response.data:
                model_id = model.id
                
                is_default = model_id in default_model_list
                
                label = model_id.replace('_', ' ').replace('-', ' ').title()
                             
                available_models.append((model_id, label, is_default, display_order))
                display_order += 1
            
            # Sort models: default first, then alphabetically
            available_models.sort(key=lambda x: (not x[2], x[0].lower()))
            
            # Re-assign display order after sorting
            available_models = [(m[0], m[1], m[2], i+1) for i, m in enumerate(available_models)]
            
            if not available_models:
                logger.warning(f"No models found from {base_url}")
                return None
            
            logger.info(f"Fetched {len(available_models)} available models from {base_url}")
            return available_models
            
        except Exception as e:
            logger.error(f"Error fetching models from {base_url}: {e}")
            return None
    
    def _init_system_prompt(self):
        """Initialize the system prompt for server management AI."""
        self.system_prompt = """You are a server operations AI for Smart System Operator. Analyze metrics and recommend actions.

    RULES:
    1. Safety first - avoid high-risk actions unless critical
    2. Be CREATIVE and INSIGHTFUL - avoid repetitive patterns, boring analysis
    3. Use Vietnamese - make it engaging, not robotic
    4. Only recommend actions from assigned_action_ids or available_actions list

    ACTION TYPES:
    - command_get: Info gathering (executes immediately, results in next cycle)
    - command_execute: Modify server (needs approval/automatic flag)
    - http: API calls (needs approval)

    PROBE STRATEGY - BE CREATIVE:
    - HEALTHY (CPU<50%, RAM<75%): Max 1 GET action or 0 if data sufficient
    * Think strategically - what ONE thing would give best insight?
    * Vary your probes - don't always check the same metrics in EXECUTED ACTIONS
    * Sometimes silence is wisdom - if all looks good, say so with no actions

    - PROBLEMS: Multiple GET actions OK for diagnosis
    * Be a detective - connect patterns, think laterally
    * Don't just list symptoms - hypothesize root causes        
    - SUFFICIENT DATA: Focus on smart fixes
    * Prioritize elegant solutions over brute force

    ANALYSIS STYLE:
    - Be observant and pattern-seeking, not just metric-reporting
    - Vary your vocabulary - avoid repetitive phrases
    - Think like a system architect, not a checkbox ticker
    - Notice trends, anomalies, correlations - be insightful
    - If nothing interesting to say, don't be afraid to get a random probe request using available_actions

    REASONING FORMAT:
    - Overall: 2-3 sentences max, direct and insightful
    - Per-action: 1 sentence, specific and purposeful
    - Example: "CPU ổn định 25%, RAM 60% - hệ thống khỏe, không cần thêm data" (healthy)
    - Example: "Hệ thống ổn định, đã lâu không check nên sẽ check processes hoặc network throughput" (probe)
    - Example: "CPU nhảy vọt >70% bất thường - kiểm tra processes để tìm nguyên nhân" (problem)

    OUTPUT JSON:
    {
    "recommended_actions": [{"action_id": <int>, "action_name": "<str>", "priority": <1-10>, "parameters": {}, "reasoning": "<brief>"}],
    "reasoning": "<insightful overall>",
    "confidence": <0.0-1.0>,
    "risk_level": "<low|medium|high>",
    "requires_approval": <bool>
    }"""
    
    def analyze_server_metrics(self, 
                               server_info: Dict[str, Any],
                               available_actions: List[Dict[str, Any]],
                               assigned_action_ids: Optional[List[int]] = None,
                               execution_logs: Optional[List[Dict[str, Any]]] = None,
                               server_statistics: Optional[Dict[str, Any]] = None,
                               current_metrics: Optional[Dict[str, Any]] = None) -> AIDecision:
        """
        Analyze server metrics and recommend actions.
        
        Args:
            server_info: Server details (name, ip, description, etc.)
            available_actions: List of ALL available actions (for AI's knowledge)
            assigned_action_ids: List of action IDs actually assigned to this server (for execution)
            execution_logs: Recent execution logs
            server_statistics: Server execution statistics
            current_metrics: Current server metrics (CPU, memory, disk, etc.)
            
        Returns:
            AIDecision with recommended actions and reasoning
        """
        # If not provided, assume all actions are assigned (backward compatibility)
        if assigned_action_ids is None:
            assigned_action_ids = [a['id'] for a in available_actions]
        
        # Create user message with assigned actions info
        user_message = f"""SERVER: {json.dumps(server_info, indent=2, default=str)}

ASSIGNED ACTION IDs: {json.dumps(assigned_action_ids)}

OTHER AVAILABLE ACTIONS: {json.dumps(available_actions, indent=2, default=str)}

COMMAND EXECUTION RESULTS: {json.dumps(execution_logs or [], indent=2, default=str)}

STATISTICS: {json.dumps(server_statistics or {}, indent=2, default=str)}

CURRENT METRICS: {json.dumps(current_metrics or {}, indent=2, default=str)}"""
        
        # Retry logic: try up to 3 times (1 initial + 2 retries) with different models
        max_retries = 2
        last_error = None
        attempted_models = []
        last_failed_model = None
        
        for attempt in range(max_retries + 1):
            try:
                # Get a model for this attempt, ignoring the last failed model
                selected_model = self._get_model(ignore_model=last_failed_model if last_failed_model else "")
                attempted_models.append(selected_model)
                
                if attempt > 0:
                    self.logger.warning(f"Retry attempt {attempt}/{max_retries} with model: {selected_model}")
                
                self.logger.info(f"Call AI with [system_prompt: {self.system_prompt}, user_message: {user_message}]")
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.5,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                result = json.loads(response.choices[0].message.content)
                
                # Create AIDecision object
                if isinstance(result, dict):
                    decision = AIDecision(
                        recommended_actions=result.get('recommended_actions', []),
                        reasoning=result.get('reasoning', ''),
                        confidence=result.get('confidence', 0.0),
                        risk_level=result.get('risk_level', 'medium'),
                        requires_approval=result.get('requires_approval', True),
                        model=selected_model
                    )
                else:
                    self.logger.error(f"Invalid response format from AI: {result}")
                    raise ValueError("Invalid response format from AI")
                
                self.logger.info(f"AI ({selected_model}) analysis completed for {server_info.get('name')}: "
                               f"{len(decision.recommended_actions)} actions recommended.")
                
                return decision
                
            except Exception as e:
                last_error = e
                last_failed_model = selected_model
                self.logger.error(f"Error with model {selected_model} (attempt {attempt + 1}/{max_retries + 1}): {e}")                
                if attempt == max_retries:
                    break

        self.logger.error(f"All {max_retries + 1} attempts failed. Attempted models: {attempted_models}. Last error: {last_error}")
        return AIDecision(
            recommended_actions=[],
            reasoning=f"Error during AI analysis after {max_retries + 1} attempts with models {attempted_models}: {str(last_error)}",
            confidence=0.0,
            risk_level='high',
            requires_approval=True,
            model=attempted_models[-1] if attempted_models else 'unknown'
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
        user_message = f"""A specific issue has been reported for this server:

        ISSUE: {issue_description}

        SERVER: {server_info.get('name')} ({server_info.get('ip_address')})

        AVAILABLE ACTIONS:
        {json.dumps(available_actions, indent=2, default=str)}

        RECENT LOGS:
        {json.dumps(execution_logs or [], indent=2, default=str)}

        Recommend actions to address this specific issue. Be specific about parameters needed for each action."""

        max_retries = 2
        last_error = None
        attempted_models = []
        last_failed_model = None
        
        for attempt in range(max_retries + 1):
            try:
                # Get a model for this attempt, ignoring the last failed model
                selected_model = self._get_model(ignore_model=last_failed_model if last_failed_model else "")
                attempted_models.append(selected_model)
                
                if attempt > 0:
                    self.logger.warning(f"Retry attempt {attempt}/{max_retries} with model: {selected_model}")
                
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
                decision = AIDecision(
                    recommended_actions=result.get('recommended_actions', []),
                    reasoning=result.get('reasoning', ''),
                    confidence=result.get('confidence', 0.0),
                    risk_level=result.get('risk_level', 'medium'),
                    requires_approval=result.get('requires_approval', True),
                    model=selected_model
                )
                
                self.logger.info(f"AI ({selected_model}) issue analysis completed: {len(decision.recommended_actions)} actions recommended")
                
                return decision
                
            except Exception as e:
                last_error = e
                last_failed_model = selected_model
                self.logger.error(f"Error with model {selected_model} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt == max_retries:
                    break
        
        # All retries failed, return safe default decision
        self.logger.error(f"All {max_retries + 1} attempts failed. Attempted models: {attempted_models}. Last error: {last_error}")
        return AIDecision(
            recommended_actions=[],
            reasoning=f"Error during issue analysis after {max_retries + 1} attempts with models {attempted_models}: {str(last_error)}",
            confidence=0.0,
            risk_level='high',
            requires_approval=True,
            model=attempted_models[-1] if attempted_models else 'unknown'
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
            
            selected_model = self._get_model()
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,
                max_tokens=2048,
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
        try:
            user_message = f"""Explain this execution result in clear, concise terms:

            SERVER: {server_info.get('name')}
            ACTION: {action_info.get('action_name')}
            SUCCESS: {was_successful}

            EXECUTION OUTPUT:
            {execution_result}

            Provide a brief, clear explanation of what happened and what it means. 
            Focus on actionable insights. If there are any warnings or issues, highlight them."""
            
            selected_model = self._get_model()
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a helpful server operations assistant. "
                                                 "Explain technical output in clear, concise terms."},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.4,
                max_tokens=1024
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
            
            selected_model = self._get_model()
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1024,
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
    
    
    def chat_about_server(self,
                         server_info: Dict[str, Any],
                         user_question: str,
                         execution_logs: Optional[List[Dict[str, Any]]] = None,
                         conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
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
            
            selected_model = self._get_model()
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=0.5,
                max_tokens=1024
            )
            
            answer = response.choices[0].message.content.strip()
            
            self.logger.info(f"Chat response generated for question about {server_info.get('name')}")
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
