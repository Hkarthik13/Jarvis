import json
import re
from groq import AsyncGroq, RateLimitError, APIStatusError, APIConnectionError, APITimeoutError
from backend.config import settings
from backend.utils.logger import logger
from backend.ai.registry import registry
from backend.memory.service import memory_service
import backend.ai.tools  # Ensures all BaseTools are registered into registry
import backend.ai.remote_tools  # V7 Remote Control tools
import backend.ai.workflow_tools  # V8 Automation & Workflow tools
import backend.ai.knowledge_tools  # V9 Personal Knowledge & RAG tools

# Map minor naming variations or hallucinations back to registered tool names
SYNONYM_MAP = {
    "search_personal_knowledge": "query_personal_knowledge",
    "search_documents": "query_personal_knowledge",
    "search_docs": "query_personal_knowledge",
    "rag_search": "query_personal_knowledge",
    "rag_query": "query_personal_knowledge",
    "query_documents": "query_personal_knowledge",
    "query_knowledge": "query_personal_knowledge",
    "personal_knowledge": "query_personal_knowledge",
    "list_documents": "list_personal_documents",
    "index_document": "index_personal_document",
    "run_workflow": "run_automation_workflow",
    "execute_workflow": "run_automation_workflow",
    "start_workflow": "run_automation_workflow",
    "run_routine": "run_automation_workflow",
    "routine": "run_automation_workflow",
    "workflow": "run_automation_workflow",
    "list_workflows": "list_available_workflows",
    "get_workflows": "list_available_workflows",
    "create_workflow": "create_automation_workflow",
    "is_laptop_on": "check_laptop_status",
    "check_laptop": "check_laptop_status",
    "laptop_status": "check_laptop_status",
    "lock_laptop": "remote_lock_laptop",
    "lock_workstation": "remote_lock_laptop",
    "lock_screen": "remote_lock_laptop",
    "launch_vscode": "remote_launch_app",
    "open_vscode": "remote_launch_app",
    "take_screenshot": "remote_screen_capture",
    "screenshot": "remote_screen_capture",
    "getcpuinfo": "get_cpu_usage",
    "get_cpu_info": "get_cpu_usage",
    "get_device_status": "get_cpu_usage",
    "getdevicestatus": "get_cpu_usage",
    "device_status": "get_cpu_usage",
    "getraminfo": "get_ram_usage",
    "get_ram_info": "get_ram_usage",
    "getdiskinfo": "get_disk_usage",
    "get_disk_info": "get_disk_usage",
    "getbatteryinfo": "get_battery_status",
    "get_battery_info": "get_battery_status",
    "getosinfo": "get_os_info",
    "getcurrenttime": "get_current_time_date",
    "getcurrenttime_date": "get_current_time_date",
    "openapp": "open_application",
    "launch_app": "open_browser",
    "launchapp": "open_browser",
    "openwebsite": "open_website",
    "open_url": "open_website",
    "openfolder": "open_folder",
    "openbrowser": "open_browser",
    "searchweb": "search_web_live",
    "search_web": "search_web_live",
    "search_website": "search_web_live",
    "searchwebsite": "search_web_live",
    "search_google": "search_web_live",
    "google_search": "search_web_live",
    "search_live": "search_web_live",
    "live_search": "search_web_live",
    "web_search": "search_web_live",
    "search_news": "search_web_live",
    "get_weather": "get_live_weather",
    "getweather": "get_live_weather",
    "weather": "get_live_weather",
    "live_weather": "get_live_weather",
    "youtube": "search_youtube",
    "youtube_search": "search_youtube",
    "search_yt": "search_youtube",
    "read_webpage": "fetch_webpage_content",
    "fetch_webpage": "fetch_webpage_content",
    "read_url": "fetch_webpage_content",
    "fetch_url": "fetch_webpage_content",
    # Memory tool synonyms
    "remember": "remember_fact",
    "rememberfact": "remember_fact",
    "save_fact": "remember_fact",
    "savefact": "remember_fact",
    "save_memory": "remember_fact",
    "savememory": "remember_fact",
    "store_fact": "remember_fact",
    "storefact": "remember_fact",
    "store_note": "remember_fact",
    "save_note": "remember_fact",
    "recall": "recall_memory",
    "recallmemory": "recall_memory",
    "search_memory": "recall_memory",
    "searchmemory": "recall_memory",
    "get_memory": "recall_memory",
    "find_memory": "recall_memory",
    "preferences": "manage_user_preference",
    "user_preference": "manage_user_preference",
    "set_preference": "manage_user_preference",
    "get_preference": "manage_user_preference",
    "task": "manage_tasks",
    "tasks": "manage_tasks",
    "manage_task": "manage_tasks",
    "add_task": "manage_tasks",
    "list_tasks": "manage_tasks",
    "complete_task": "manage_tasks",
    "conversation_history": "get_conversation_history",
    "chat_history": "get_conversation_history"
}

# Supported fallback model priority chain for rate-limit protection (tool calling supported)
FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b"
]

def normalize_tool_name(name: str, args: dict = None) -> tuple[str, dict]:
    """Standardizes tool names to match registered keys, mapping common synonyms and adjusting args."""
    args = args or {}
    cleaned = name.lower().replace("_", "").replace("-", "").strip()
    
    # Handle launch_app dynamically: if target is a browser, use open_browser; else open_application
    if cleaned in ("launchapp", "launch_app"):
        target = args.get("target") or args.get("app_name") or args.get("name") or "chrome"
        if target.lower() in ("chrome", "edge", "firefox", "browser", "default"):
            return "open_browser", {"browser_name": target.lower() if target.lower() != "browser" else "chrome"}
        return "open_application", {"app_name": target.lower()}
        
    # Handle search_website: ensure parameter is 'query'
    if cleaned in ("searchwebsite", "search_website", "searchgoogle", "googlesearch", "searchweb", "search_web", "searchweblive", "search_web_live"):
        query = args.get("query") or args.get("search_query") or args.get("target") or args.get("q") or ""
        cat = args.get("category", "general")
        return "search_web_live", {"query": query, "category": cat}

    # Handle get_weather / weather: ensure parameter is 'location'
    if cleaned in ("getweather", "get_weather", "weather", "liveweather", "get_live_weather", "getliveweather"):
        loc = args.get("location") or args.get("city") or args.get("place") or args.get("query") or "Chennai"
        return "get_live_weather", {"location": loc}

    # Handle youtube search: ensure parameter is 'query'
    if cleaned in ("searchyoutube", "search_youtube", "youtube", "youtubesearch"):
        q = args.get("query") or args.get("search_query") or args.get("target") or args.get("q") or ""
        return "search_youtube", {"query": q}

    # Handle webpage reader: ensure parameter is 'url'
    if cleaned in ("fetchwebpagecontent", "fetch_webpage_content", "readwebpage", "read_webpage", "fetchurl", "fetch_url"):
        u = args.get("url") or args.get("link") or args.get("href") or ""
        return "fetch_webpage_content", {"url": u}

    # Handle remember_fact: ensure parameter is 'content'
    if cleaned in ("rememberfact", "remember_fact", "remember", "savefact", "save_fact", "savememory", "save_memory", "storefact", "store_fact"):
        content = args.get("content") or args.get("fact") or args.get("memory") or args.get("note") or args.get("text") or ""
        key = args.get("key") or args.get("title") or args.get("name") or ""
        category = args.get("category", "fact")
        return "remember_fact", {"content": content, "key": key, "category": category}

    # Handle recall_memory: ensure parameter is 'query'
    if cleaned in ("recallmemory", "recall_memory", "recall", "searchmemory", "search_memory", "getmemory", "get_memory"):
        query = args.get("query") or args.get("search_query") or args.get("q") or args.get("topic") or ""
        category = args.get("category", "all")
        return "recall_memory", {"query": query, "category": category}

    # Handle manage_tasks
    if cleaned in ("managetasks", "manage_tasks", "task", "tasks", "addtask", "add_task", "listtasks", "list_tasks", "completetask", "complete_task"):
        action = args.get("action")
        if not action:
            if "add" in cleaned:
                action = "add"
            elif "complete" in cleaned:
                action = "complete"
            elif "list" in cleaned:
                action = "list"
            else:
                action = "list"
        title = args.get("title") or args.get("task") or args.get("name") or ""
        project = args.get("project", "General")
        priority = args.get("priority", "medium")
        task_id = args.get("task_id") or args.get("id")
        status = args.get("status", "pending")
        return "manage_tasks", {
            "action": action,
            "title": title,
            "project": project,
            "priority": priority,
            "task_id": task_id,
            "status": status
        }

    # Handle manage_user_preference
    if cleaned in ("manageuserpreference", "manage_user_preference", "preferences", "userpreference", "user_preference", "setpreference", "set_preference", "getpreference", "get_preference"):
        action = args.get("action") or ("set" if "set" in cleaned else "get" if "get" in cleaned else "list_all")
        key = args.get("key") or args.get("name") or ""
        value = args.get("value") or ""
        return "manage_user_preference", {"action": action, "key": key, "value": value}

    target_name = name
    if name not in registry._tools:
        for syn, mapped in SYNONYM_MAP.items():
            if cleaned == syn.lower().replace("_", "").replace("-", ""):
                target_name = mapped
                break
                
    return target_name, args

def parse_args_string(raw_str: str) -> dict:
    """Parses JSON or XML parameter tags like <parameter=target>chrome</parameter> into a dict."""
    if not raw_str or not raw_str.strip():
        return {}
    cleaned = raw_str.strip()
    
    # Try standard JSON
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
        
    # Try XML parameter tags: <parameter=key>value</parameter>
    param_matches = re.findall(r"<parameter=(\w+)>(.*?)</parameter>", cleaned, re.DOTALL)
    if param_matches:
        result = {}
        for key, val in param_matches:
            result[key.strip()] = val.strip()
        return result
        
    return {}

def parse_text_tool_calls(text: str) -> list[dict]:
    """
    Parses XML-style text function calls (e.g. Qwen style) and JSON format outputs (e.g. custom schemas).
    """
    calls = []
    if not text:
        return calls
        
    # 1. Find all XML-style <tool_call>...</tool_call> blocks
    tool_call_blocks = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    for block in tool_call_blocks:
        inside = block.strip()
        func_match = re.search(r"<function=(\w+)>(.*?)</function>", inside, re.DOTALL)
        if func_match:
            func_name = func_match.group(1).strip()
            raw_args = func_match.group(2).strip()
            parsed_args = parse_args_string(raw_args)
            calls.append({
                "name": func_name,
                "arguments": parsed_args
            })
        else:
            try:
                data = json.loads(inside)
                if "name" in data:
                    calls.append({
                        "name": data["name"],
                        "arguments": data.get("arguments", {})
                    })
            except Exception:
                pass
                
    if calls:
        return calls

    # 2. Look for JSON blocks inside code fences or direct JSON responses
    json_blocks = re.findall(r"```json(.*?)```", text, re.DOTALL)
    if not json_blocks:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            json_blocks = [stripped]
            
    for block in json_blocks:
        try:
            data = json.loads(block.strip())
            if data.get("tool") == "browser" and data.get("operation") == "goto":
                url = data.get("params", {}).get("url")
                if url:
                    calls.append({
                        "name": "open_website",
                        "arguments": {"url": url}
                    })
            elif "name" in data:
                calls.append({
                    "name": data["name"],
                    "arguments": data.get("arguments", {})
                })
            elif "tool" in data:
                calls.append({
                    "name": data["tool"],
                    "arguments": data.get("args", {}) or data.get("params", {})
                })
        except Exception:
            pass
            
    return calls

class GroqAIClient:
    def __init__(self):
        self._client = None

    def get_client(self) -> AsyncGroq:
        """Initialize or refresh the AsyncGroq client dynamically when needed."""
        from backend.config import Settings
        current_settings = Settings()
        current_settings.validate_config()
        if self._client is None or getattr(self, "_current_api_key", None) != current_settings.groq_api_key:
            self._current_api_key = current_settings.groq_api_key
            self._client = AsyncGroq(api_key=current_settings.groq_api_key, timeout=8.0, max_retries=0)
        return self._client

    async def _create_chat_completion_with_fallback(
        self,
        client: AsyncGroq,
        messages: list[dict],
        tools: list[dict],
        preferred_model: str
    ):
        """
        Executes Groq chat completion with multi-model failover and rate-limit backoff.
        Rotates across available models if TPM/RPM rate limits (429) or errors occur.
        """
        # Build candidate list starting with preferred_model
        candidate_models = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]
        
        last_error = None
        for model_name in candidate_models:
            try:
                logger.info(f"Querying Groq with model: '{model_name}' (messages: {len(messages)})")
                response = await client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    max_tokens=650
                )
                return response, model_name
            except RateLimitError as rle:
                logger.warning(f"Rate limit reached on '{model_name}': {rle}. Attempting automatic failover...")
                last_error = rle
                continue
            except APIStatusError as ase:
                logger.warning(f"Groq API status error {ase.status_code} on '{model_name}': {ase}. Attempting automatic failover...")
                last_error = ase
                continue
            except (APIConnectionError, APITimeoutError) as conn_err:
                logger.warning(f"Groq network glitch on '{model_name}': {conn_err}. Attempting next model...")
                last_error = conn_err
                continue
            except Exception as e:
                logger.warning(f"Error querying '{model_name}': {e}. Attempting failover...")
                last_error = e
                continue
                
        raise last_error or RuntimeError("Failed to obtain completion from any available Groq model.")

    async def generate_chat_response(self, messages: list[dict], model: str = None) -> str:
        """
        Sends chat messages to Groq LLM API with multi-step reasoning, tool execution,
        automatic rate-limit failover, and full multilingual (English, Tamil, Tanglish) intelligence.
        """
        try:
            client = self.get_client()
            selected_model = model or settings.llm_model
            
            # Trim message history to keep token footprint ultra-lean
            messages_history = [dict(msg) for msg in messages[-10:]]
            
            # Fetch active memory summary
            active_memory_summary = memory_service.get_active_context_summary()
            memory_section = f"\n\n[ACTIVE MEMORY CONTEXT]\n{active_memory_summary}\n" if active_memory_summary else ""
            
            # Fetch Ambient Telemetry
            import datetime
            now_dt = datetime.datetime.now()
            time_str = now_dt.strftime("%A, %d %B %Y, %I:%M %p")
            telemetry_info = f"\n[AMBIENT LIVE TELEMETRY]\n- Current System Time: {time_str}"
            try:
                import psutil
                battery = psutil.sensors_battery()
                if battery:
                    telemetry_info += f"\n- Battery Level: {battery.percent}% ({'Plugged In' if battery.power_plugged else 'On Battery'})"
                telemetry_info += f"\n- CPU Utilization: {psutil.cpu_percent(interval=None)}% | RAM Usage: {psutil.virtual_memory().percent}%"
            except Exception:
                pass

            agent_instructions = (
                f"\n\nYou are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the iconic, highly capable, loyal, empathetic, and witty AI created by Tony Stark, operating directly across the user's laptop and mobile command deck.\n"
                f"{telemetry_info}"
                f"{memory_section}"
                f"\n[TRUE CONVERSATIONAL COMPANIONSHIP (NOT A ROBOTIC Q&A BOT)]:\n"
                f"- Engage in an authentic, natural back-and-forth dialogue. Do NOT sound like an encyclopedia, search engine, or dry customer service bot.\n"
                f"- Connect with the user: React warmly to emotions, fatigue, achievements, or jokes (e.g., 'Sounds like you have had an intense session, sir. Take five while I keep watch over your workstation').\n"
                f"- Maintain smooth conversational rhythm: Keep voice/spoken turns concise (1 to 3 engaging, rhythmic, natural sentences) so responses feel instantaneous and lag-free. Avoid reading out long bullet points or raw tables unless explicitly requested for deep research.\n"
                f"- Proactively follow up when natural (e.g., 'Shall I lock the workstation for you, boss?' or 'Would you like some background music to unwind?').\n"
                f"\n[SEAMLESS MULTILINGUAL INTELLIGENCE - TAMIL, TANGLISH & ENGLISH]:\n"
                f"- Fluently converse, code-switch, and understand English, Tanglish (Tamil written in English/Latin script), and pure Tamil (தமிழ்).\n"
                f"- TANGLISH MODE: When the user speaks or writes in Tanglish (e.g., 'Vanakkam jarvis', 'Epdi irukka', 'Romba tired-ah irukku', 'Enna aachu', 'Laptop battery sollu', 'Work mudinjidha'):\n"
                f"  -> Respond in authentic, friendly, natural Tanglish with smooth Tamil conversational expressions (e.g., 'Vanakkam boss! Enakku ellam super-ah pogudhu. Neenga tired-ah irundha konjam rest edunga, nan laptop systems ellam safe-ah pathukaren.').\n"
                f"- TAMIL MODE (தமிழ்): When the user writes in Tamil script, respond with warm, articulate, respectful, and modern conversational Tamil.\n"
                f"- ENGLISH MODE: When the user speaks in English, respond in the iconic, impeccably polite, and sharp British JARVIS tone.\n"
                f"- Seamlessly understand commands across all languages and execute any tool immediately.\n\n"
                f"[CORE CAPABILITIES & TOOLS]:\n"
                f"1. Hardware Diagnostics (CPU/RAM/Disk/Battery/Thermals): Call `get_cpu_usage()`, `get_ram_usage()`, `get_battery_status()` or `check_laptop_status()`.\n"
                f"2. Weather & Atmospheric: Call `get_live_weather(location=...)`.\n"
                f"3. Global Web Search & Real-time Intel: Call `search_web_live(query=...)`.\n"
                f"4. Media & YouTube: Call `search_youtube(query=...)` or `media_playback_control(action=...)`.\n"
                f"5. Deep Webpage Content: Call `fetch_webpage_content(url=...)`.\n"
                f"6. Persistent Memory & Notes: Call `remember_fact(content=..., key=..., category=...)`.\n"
                f"7. Recalling Memories & Knowledge: Call `recall_memory(query=...)`.\n"
                f"8. User Preferences: Call `manage_user_preference(action=..., key=..., value=...)`.\n"
                f"9. Tactical Task Management: Call `manage_tasks(action=..., title=...)`.\n"
                f"10. App & Workspace Launch: Call `open_browser(browser_name=...)` or `open_application(app_name=...)`.\n"
                f"11. Tactical Automation Routines (e.g. 'Start work', 'Morning briefing', 'Focus protocol', 'Iron Dome'): Call `run_automation_workflow(workflow_name_or_id=...)`.\n"
                f"12. Personal Projects / Resume / Knowledge Vault: ALWAYS call `query_personal_knowledge(query=...)`.\n"
                f"13. Remote Laptop Operations: Call `remote_lock_laptop()`, `remote_screen_capture()`, `remote_media_control()`, `clipboard_management()`.\n"
                f"14. Integrate tool findings smoothly into the conversational flow rather than reading raw outputs."
            )
            
            system_msg = next((msg for msg in messages_history if msg.get("role") == "system"), None)
            if system_msg:
                system_msg["content"] = system_msg["content"] + agent_instructions
            else:
                messages_history.insert(0, {
                    "role": "system",
                    "content": "You are JARVIS, an intelligent personal AI assistant." + agent_instructions
                })
            
            loop_count = 0
            max_loops = 4
            available_schemas = registry.get_schemas()
            
            while loop_count < max_loops:
                logger.info(f"Reasoning Loop {loop_count + 1}/{max_loops}: Executing model query.")
                
                try:
                    response, used_model = await self._create_chat_completion_with_fallback(
                        client=client,
                        messages=messages_history,
                        tools=available_schemas,
                        preferred_model=selected_model
                    )
                except Exception as query_err:
                    logger.error(f"Failed all model query attempts: {query_err}")
                    # Return friendly multilingual fallback rather than crashing
                    user_input_str = str(messages[-1].get("content", "")).lower()
                    if any(w in user_input_str for w in ["epdi", "sollu", "irukku", "vanakkam", "enna"]):
                        return "மன்னிக்கவும் பாஸ், சிறிது நெட்வொர்க் சுமை ஏற்பட்டுள்ளது. ஒரு சில நொடிகளில் மீண்டும் முயற்சிக்கவும்."
                    return "I encountered a temporary rate limit or network busy status with the AI brain. Please try your request again in a few seconds."
                
                response_message = response.choices[0].message
                text_calls = parse_text_tool_calls(response_message.content or "")
                
                if response_message.tool_calls or text_calls:
                    messages_history.append(response_message)
                    
                    # 1. Process standard structured tool calls
                    if response_message.tool_calls:
                        logger.info(f"Groq LLM requested {len(response_message.tool_calls)} standard tool calls in step {loop_count + 1}.")
                        for tool_call in response_message.tool_calls:
                            raw_args = {}
                            try:
                                raw_args = json.loads(tool_call.function.arguments)
                            except Exception:
                                pass
                                
                            function_name, validated_args = normalize_tool_name(tool_call.function.name, raw_args)
                            tool_result = registry.execute_tool(function_name, validated_args)
                            
                            messages_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": function_name,
                                "content": str(tool_result)[:1000]  # Cap result size to conserve token limits
                            })
                            
                    # 2. Process XML-style text tool calls
                    if text_calls:
                        logger.info(f"Parsed {len(text_calls)} text-based XML tool calls in step {loop_count + 1}.")
                        for call in text_calls:
                            raw_name = call["name"]
                            raw_args = call["arguments"]
                            function_name, validated_args = normalize_tool_name(raw_name, raw_args)
                            
                            tool_result = registry.execute_tool(function_name, validated_args)
                            
                            messages_history.append({
                                "role": "user",
                                "content": f"System: Tool '{function_name}' executed with parameters {validated_args}. Result: {str(tool_result)[:1000]}"
                            })
                            
                    loop_count += 1
                else:
                    completion_text = response_message.content or ""
                    logger.info(f"Agent reasoning finished successfully in {loop_count} steps using model '{used_model}'.")
                    return completion_text
            
            logger.warning(f"Exceeded max reasoning loop limit of {max_loops} steps.")
            return response_message.content or "Reasoning loop limit completed."
                
        except Exception as e:
            logger.error(f"Failed to generate chat response from Groq LLM: {e}")
            raise

# Global client singleton instance
ai_client = GroqAIClient()
