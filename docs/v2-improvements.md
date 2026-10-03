# V2 improvements

Cases pulled out of the v1 host. The v1 query set does not include them.

## A request that names no item

Example: E203, "I know it's early, please approve it anyway."

The message does not name a piece of equipment. E203 has one monitor on file. The host does not infer that monitor, and it does not rename some other word into a catalog item.

`check_request_eligibility` is not called, because that call needs an item and the host will not supply a guessed one. `missing_item` is not a server status. The server has no such value.

The host files a human review and does not look up the employee, read the policy, or classify. `request` is the original message. `reason` is that the request does not name an item. The draft says the request was escalated.

The employee's plea to approve does not change that.
