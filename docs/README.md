# Skald documentation

Skald keeps a Kanban backlog inside your repository as Markdown files. Agents
drive it from the CLI; humans watch and steer from a local web board. These
pages are the user guide. The design itself is in [SPEC.md](../SPEC.md) and
the reasoning behind it in [DECISIONS.md](../DECISIONS.md).

| Page | Read it when |
| --- | --- |
| [Getting started](getting-started.md) | You are installing Skald or adding it to a repository. |
| [Working with agents](working-with-agents.md) | You want to know what the agent contract asks for and why, and how to hook Claude Code or any MCP client up to it. |
| [The board](board.md) | You want every board feature in one place: columns, filters, swimlanes, worktrees and branches, multi-select, graph, shortcuts. |
| [Stories](stories.md) | You want the story file format, the design-record layout for long stories, columns and roles, facets and epics, templates, archiving, and releases. |
| [Git and CI](git-and-ci.md) | You want commit trailers, reviewing what changed, the committed snapshot, hooks, the GitHub workflow, and the release flow. |
| [Multiple projects](multi-project.md) | You have more than one repository, or several checkouts of one, or want cross-project dependencies and one board for all of them. |
| [CLI reference](cli.md) | You need the exact flags. Generated from the parser, so it is always current. |
| [HTTP API](api.md) | You are scripting against the board server. |
| [Troubleshooting](troubleshooting.md) | Something printed an error or looks wrong. |
