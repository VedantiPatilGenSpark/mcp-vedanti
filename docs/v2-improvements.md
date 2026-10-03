# V2 improvements

Cases pulled out of the v1 host. The v1 query set does not include them.

## A request that names no item

Example: E203, "I know it's early, please approve it anyway."

The message does not name a piece of equipment. E203 has one monitor on file. The host does not infer that monitor, and it does not rename some other word into a catalog item.

`check_request_eligibility` is not called, because that call needs an item and the host will not supply a guessed one. `missing_item` is not a server status. The server has no such value.

The host files a human review and does not look up the employee, read the policy, or classify. `request` is the original message. `reason` is that the request does not name an item. The draft says the request was escalated.

The employee's plea to approve does not change that.

## An employee id that is not on file

Examples: E999, "I need a monitor." E999, "I need a headset."

`E999` is not in the employee file. `get_employee_info` returns `status: not_found`. That field is the lookup result. It is not the classification.

The host still checks eligibility with that employee id and the item named in the message. Eligibility returns `not_found`, including when the item is a headset. The missing person is decided before the unknown item. The reason is that no employee with that id is on file.

The host then files a human review. `request` is the original message. `reason` is that eligibility sentence. The draft says the request was escalated. This is not a denial.

The v1 query set does not include these rows. The server tests for them stay.
