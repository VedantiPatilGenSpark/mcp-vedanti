# Why item extract runs before ReAct

The host makes one model call to name the item, then starts the ReAct tool loop. That call is not a tool and is not part of the eight-step budget.

## The cost

One extra `complete()` and a second JSON shape. On a clean request that is more latency than “first ReAct thought names the item.”

ReAct already spends a call per tool step, up to eight, plus a reflector pass. The expensive failure is not the prelude. It is the model guessing an item, calling tools, getting blocked, and burning the step limit.

## What the prelude buys

Eligibility needs exactly one item. “Please approve it anyway” names none. “I want a monitor and a laptop” names two. Those must escalate without `check_request_eligibility`. If that decision sits inside ReAct, a confused model can loop until timeout. One extract call is cheaper than eight failed tool steps.

The same call is where meaning is allowed. `headphones` may become `headset`. `computer` must not become `laptop`. That judgment is not a host word list and not a server `strip().lower()`. Binding the item before tools keeps a bad synonym from being classified as if it were real.

## What we did not do

We did not copy the catalog onto the host. We did not add an extract MCP tool. We did not replace ReAct. After one item is bound, the model still chooses tools. That remains the demo.

The reflector stays a second model pass on wording. Extract is the other place an extra call is worth it: it prevents a wrong item from entering the loop.
