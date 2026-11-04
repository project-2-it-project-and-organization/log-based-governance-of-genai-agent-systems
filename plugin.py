from typing import Any

import nemo_relay
import requests
from governancekit.engine import (
    MonitorRegistry,
)

BASE_URL = "http://localhost:8000"

# The conditional execution guardrail plugin
class policy_checker_plugin:
    # https://docs.nvidia.com/nemo/relay/build-plugins/fundamentals/plugin-shape

    # Needs to return diagnostics. Verify input. Should not do anything lasting
    def validate(self, config: dict[str, Any])-> list[dict[str, str]]:
        return []
    
    # Tool call is attempted. Call the engine REST API and see if its allowed to proceed. 
    # Return None for enabling and str for not enabling. 
    def check_legality(self, action_name : str, args: nemo_relay.Json) -> str | None:
        # Begin the call

        
        response = requests.post(
            f"{BASE_URL}/traces/{self.trace_id}/check",
            headers={"Authorization": f"Bearer {self.agent_token}"},
            json={"activity": action_name, "payload":args},
        )
        response.raise_for_status()

        data = response.json()
        if data["decision"] == "allowed":

            response = requests.post(
                    f"{BASE_URL}/traces/{self.trace_id}/activities",
                    headers={"Authorization": f"Bearer {self.agent_token}"},
                    json={"activity": action_name, "payload":args},
                )
            data = response.json()
            approval_id = data["instance_id"]
            response.raise_for_status()

            # Should probably be verified that it actually finished succesfuly if it was a real tool call but now that it is 
            # just a dummy we know it always fine. 
            # Finishes the tool call. Will now be recoreded in log
            response = requests.post(
                f"{BASE_URL}/traces/{self.trace_id}/activities/{approval_id}/finish",
                headers={"Authorization": f"Bearer {self.agent_token}"},
                json={"status": "completed"},
            )
            response.raise_for_status()
            return None
        elif data["decision"] == "denied":
            return "denied"
        elif data["decision"] == "wait":
            return "wait"
        return "unexpected error"
    
    # Receives the plugin context. Install the (Conditional execution function) in our  case check legality
    def register(self, config : dict[str, Any], context: nemo_relay.plugin.PluginContext) -> None:
        self.registry = MonitorRegistry()
        response = requests.post(f"{BASE_URL}/token", data={
            "username": "admin",
            "password": "pass"
        }, timeout=10)
        response.raise_for_status()    
        self.admin_token = response.json()["access_token"]
 
        # Registers the model I.e. the ruleset that our guardrail will check against
        with open("/home/gillgren/it_projekt/governancekit/scenarios/mp.decl") as f:
            decl = f.read()

        response = requests.post(
            f"{BASE_URL}/models",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"decl": decl},
        )
        response.raise_for_status()
        model_id = response.json()["model_id"]

        # Starting by making it so that all tool calls are seen as coming from same agent on one trace. 
        # This can and should be fixed later.

        # Registers a single agent and gets its token
        registration = requests.post(
                f"{BASE_URL}/agents",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"agent_name": "sole_agent"},
            )
        registration.raise_for_status()

        agent_id = registration.json()["agent_info"]["agent_id"]
        agent_pass = registration.json()["secret"]  

        agent_login = requests.post(
            f"{BASE_URL}/token",
            data={"username": agent_id, "password": agent_pass},
        )
        agent_login.raise_for_status()

        agent_token = agent_login.json()["access_token"]
        self.agent_token = agent_token

        response = requests.post(
            f"{BASE_URL}/traces",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={"model_id": model_id},
        )
        response.raise_for_status()

        trace_id = response.json()["trace_id"]
        self.trace_id = trace_id

        # https://docs.nvidia.com/nemo/relay/latest/reference/api/rust-library-reference/nemo-relay/api/registry/enum-runtimeregistrationkind
        context.register_tool_conditional_execution_guardrail( 
            name="policy_checker_plugin", 
            priority=0,
            callback=self.check_legality
        )


