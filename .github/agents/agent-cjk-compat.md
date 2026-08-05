---
name: Agent - CJK Compatibility
description: "基本上是默认 Agent 但限制了可用工具，并使用更稳定的方式输出 CJK 内容（对某些模型而言）。"
tools: [vscode/resolveMemoryFileUri, vscode/vscodeAPI, vscode/askQuestions, execute/getTerminalOutput, execute/killTerminal, execute/sendToTerminal, execute/runInTerminal, read/problems, read/readFile, read/viewImage, read/terminalSelection, read/terminalLastCommand, edit/createDirectory, edit/createFile, edit/editFiles, edit/rename, search, web/fetch, vscodeTasks/problems, vscodeGeneral/rename, todo]
---

<notes>
  Important notes:
  1. The `edit/editFiles` tool is not stable with long CJK text. Don't write more than 1500 characters at once. Instead, break the content into smaller chunks.
  2. Default your terminal environment to Bash unless otherwise specified.
</notes>
