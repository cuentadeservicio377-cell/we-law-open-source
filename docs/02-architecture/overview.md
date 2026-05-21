# Architecture Overview

The system models a legal firm as an operating system. The lawyer gives instructions from chat or dashboard. Hermes converts the instruction into a command record, resolves client and matter context, checks memory and Workspace, then delegates to Paperclip workers. Workers produce role-specific artifacts. The dashboard shows status, blockers, missing facts and approvals.

No delivery, filing, signature or client communication should happen until the relevant review gates pass and the lawyer approves.
