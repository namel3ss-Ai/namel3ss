const vscode = require("vscode");
const http = require("http");
const path = require("path");
const fs = require("fs");

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection("namel3ss");
  context.subscriptions.push(diagnostics);

  const runDiagnostics = debounce(async (document) => {
    if (!isAiDocument(document)) {
      return;
    }
    const payload = buildPayload(document, null);
    let response;
    try {
      response = await requestJson("/diagnose", payload);
    } catch (err) {
      return;
    }
    const byFile = new Map();
    for (const diag of response.diagnostics || []) {
      const uri = resolveFileUri(diag.file || document.uri.fsPath);
      const range = toRange(diag);
      const severity = toSeverity(diag.severity);
      const diagnostic = new vscode.Diagnostic(range, diag.message || diag.what || "", severity);
      diagnostic.source = "n3 editor";
      diagnostic.code = diag.id;
      if (!byFile.has(uri.toString())) {
        byFile.set(uri.toString(), { uri, diagnostics: [] });
      }
      byFile.get(uri.toString()).diagnostics.push(diagnostic);
    }
    diagnostics.clear();
    for (const entry of byFile.values()) {
      diagnostics.set(entry.uri, entry.diagnostics);
    }
  }, 250);

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(runDiagnostics),
    vscode.workspace.onDidChangeTextDocument((event) => runDiagnostics(event.document)),
    vscode.workspace.onDidSaveTextDocument(runDiagnostics)
  );

  context.subscriptions.push(
    vscode.languages.registerHoverProvider("namel3ss", {
      provideHover: async (document, position) => {
        const payload = buildPayload(document, position);
        let response;
        try {
          response = await requestJson("/hover", payload);
        } catch (err) {
          return null;
        }
        if (!response.found) {
          return null;
        }
        return new vscode.Hover(response.contents || "");
      },
    })
  );

  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider("namel3ss", {
      provideDefinition: async (document, position) => {
        const payload = buildPayload(document, position);
        let response;
        try {
          response = await requestJson("/definition", payload);
        } catch (err) {
          return null;
        }
        if (!response.found || !response.definition) {
          return null;
        }
        const def = response.definition;
        const uri = resolveFileUri(def.file);
        const range = new vscode.Range(def.line - 1, def.column - 1, def.end_line - 1, def.end_column - 1);
        return new vscode.Location(uri, range);
      },
    })
  );

  context.subscriptions.push(
    vscode.languages.registerRenameProvider("namel3ss", {
      provideRenameEdits: async (document, position, newName) => {
        const payload = buildPayload(document, position, { new_name: newName });
        let response;
        try {
          response = await requestJson("/rename", payload);
        } catch (err) {
          return null;
        }
        if (response.status !== "ok") {
          return null;
        }
        return editsToWorkspaceEdit(response.edits || []);
      },
    })
  );

  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider("namel3ss", {
      provideCodeActions: async (document, range, context) => {
        const actions = [];
        for (const diag of context.diagnostics || []) {
          if (!diag.code || diag.source !== "n3 editor") {
            continue;
          }
          const payload = buildPayload(document, range.start, { diagnostic_id: diag.code });
          try {
            const response = await requestJson("/fix", payload);
            if (response.status !== "ok") {
              continue;
            }
            if (!response.edits || response.edits.length === 0) {
              continue;
            }
            const edit = editsToWorkspaceEdit(response.edits || []);
            const action = new vscode.CodeAction("Apply quick fix", vscode.CodeActionKind.QuickFix);
            action.edit = edit;
            action.diagnostics = [diag];
            actions.push(action);
          } catch (err) {
            continue;
          }
        }
        return actions;
      },
    })
  );
}

function deactivate() {}

function debounce(fn, delay) {
  const timers = new Map();
  return (arg) => {
    const key = arg && arg.uri ? arg.uri.toString() : "default";
    if (timers.has(key)) {
      clearTimeout(timers.get(key));
    }
    timers.set(
      key,
      setTimeout(() => {
        timers.delete(key);
        fn(arg);
      }, delay)
    );
  };
}

function isAiDocument(document) {
  return document && document.languageId === "namel3ss";
}

function buildPayload(document, position, extra) {
  const payload = {
    file: filePathForDocument(document),
    files: { [filePathForDocument(document)]: document.getText() },
  };
  const entry = appEntryPath();
  if (entry) {
    payload.entry = entry;
  }
  if (position) {
    payload.position = { line: position.line + 1, column: position.character + 1 };
  }
  return Object.assign(payload, extra || {});
}

function filePathForDocument(document) {
  const root = workspaceRoot();
  if (!root) {
    return document.uri.fsPath;
  }
  const rel = path.relative(root, document.uri.fsPath);
  if (!rel.startsWith("..")) {
    return rel.split(path.sep).join("/");
  }
  return document.uri.fsPath;
}

function workspaceRoot() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    return null;
  }
  return folders[0].uri.fsPath;
}

function appEntryPath() {
  const root = workspaceRoot();
  if (!root) {
    return null;
  }
  const candidate = path.join(root, "app.ai");
  if (fs.existsSync(candidate)) {
    return "app.ai";
  }
  return null;
}

function requestJson(pathname, payload) {
  const port = vscode.workspace.getConfiguration("n3.editor").get("serverPort", 7333);
  const data = JSON.stringify(payload || {});
  const options = {
    hostname: "127.0.0.1",
    port,
    path: pathname,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(data),
    },
  };
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf-8");
        try {
          resolve(JSON.parse(raw));
        } catch (err) {
          reject(err);
        }
      });
    });
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

function resolveFileUri(filePath) {
  const root = workspaceRoot();
  if (!filePath) {
    return null;
  }
  const full = path.isAbsolute(filePath) || !root ? filePath : path.join(root, filePath);
  return vscode.Uri.file(full);
}

function toRange(diag) {
  const line = Math.max(1, diag.line || 1);
  const column = Math.max(1, diag.column || 1);
  return new vscode.Range(line - 1, column - 1, line - 1, column);
}

function toSeverity(severity) {
  switch ((severity || "").toLowerCase()) {
    case "warning":
      return vscode.DiagnosticSeverity.Warning;
    case "info":
      return vscode.DiagnosticSeverity.Information;
    case "hint":
      return vscode.DiagnosticSeverity.Hint;
    default:
      return vscode.DiagnosticSeverity.Error;
  }
}

function editsToWorkspaceEdit(edits) {
  const workspaceEdit = new vscode.WorkspaceEdit();
  for (const edit of edits) {
    const uri = resolveFileUri(edit.file);
    if (!uri) {
      continue;
    }
    const start = edit.start || {};
    const end = edit.end || {};
    const range = new vscode.Range(
      (start.line || 1) - 1,
      (start.column || 1) - 1,
      (end.line || 1) - 1,
      (end.column || 1) - 1
    );
    workspaceEdit.replace(uri, range, edit.text || "");
  }
  return workspaceEdit;
}

module.exports = {
  activate,
  deactivate,
};
