# mcp-vedanti

Dev container for the IT equipment-request MCP lab.

The app directory on this Mac is `/Users/VedantiV.Patil/MCP_Vedanti`. Opening that folder in a dev container bind-mounts it to `/workspaces/MCP_Vedanti` inside the container. Files you edit in the container are the same files on the Mac.

## Open the container

1. Docker Desktop is running.
2. In Cursor: **File → Open Folder** and choose `/Users/VedantiV.Patil/MCP_Vedanti`.
3. Command Palette → **Dev Containers: Reopen in Container**.

Python 3.12, `mcp`, and `pytest` are installed in the image. The GitHub CLI is added by the dev container feature, so `gh` is available inside the container after you sign in.
