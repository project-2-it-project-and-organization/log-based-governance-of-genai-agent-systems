import asyncio
from collections.abc import AsyncIterator
from typing import TypedDict

from plugin import policy_checker_plugin

import nemo_relay
import nemo_relay.plugin

# Executes two tool calls described in governancekit model. view account which should fail.
# And verify idendity which should succeed. These are the first two calls in the scenario listed in governancekit/scenarios/demo.sh

# All tools are dummy

# Tool verify_idendity
async def verify_idendity(args) -> nemo_relay.ToolExecutionResult:
    print("Verifing idendity!")
    return nemo_relay.ToolExecutionResult({"status": "ok"}) 

# Tool view_account
async def view_account() -> nemo_relay.ToolExecutionResult:
    print("Viewing the account!")
    return nemo_relay.ToolExecutionResult({"status": "ok"}) 

async def main() -> None:

    nemo_relay.plugin.register("policy_checker_plugin", policy_checker_plugin())
    config = nemo_relay.plugin.PluginConfig()
    diagnostics = nemo_relay.plugin.validate(config, "plugin.toml") # Should be fine without explicit file path also
    # Runs the register function in the plugin.
    activation = await nemo_relay.plugin.initialize(config, "plugin.toml")
    try:
        # creates a scope called demo-agent. This acts as the closest thing to an agent in this loop
        with nemo_relay.scope.scope("demo-agent", nemo_relay.ScopeType.Agent) as handle:
            try:
                tool_result = await nemo_relay.tools.execute("view_account", {}, view_account, handle=handle)
            except RuntimeError as e:
                print(f"RUNTIME ERROR for tool call 1: {e}")
            try:
                tool_result_scam = await nemo_relay.tools.execute("verify_idendity", {"method": "bankid"}, verify_idendity, handle=handle)
            except RuntimeError as e:
                print(f"RUNTIME ERROR for tool call 2: {e}")

            await nemo_relay.subscribers.flush_async()
    # Close the plugin
    finally: await activation.close()


asyncio.run(main())
