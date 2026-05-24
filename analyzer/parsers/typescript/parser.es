const ts = require("typescript");
const fs = require("fs");
const path = require("path");

// --- input ---
const filePath = process.argv[2];
const projectRoot = process.argv[3];
if (!filePath) {
  console.error("Usage: node analyze.js <file>");
  process.exit(1);
}

let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => {
  source += chunk;
});
process.stdin.on("end", () => {
  // --- parse ---
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );

  // --- IR helpers ---
  function getModifiers(node) {
    return node.modifiers ? node.modifiers.map(m => ts.SyntaxKind[m.kind]) : [];
  }

  function formatPathToNamespace(filePath) {
    return filePath
      // normalize slashes
      .replace(/\\/g, "/")
      // remove final extension only
      .replace(/\.[^/.]+$/, "")
      // convert separators to dots
      .replace(/\//g, ".");
  }
  const aliasMap = {
    '@': projectRoot, // map your `@` to your project root
  };

  function resolvePath(
    rootDir,
    importPath     // e.g. "../utils" | "./utils" | "@/utils"
  ) {
    let resolved;

    // 1. Handle root alias "@/..."
    if (importPath.startsWith("@/")) {
      resolved = path.join(rootDir, importPath.slice(2));
    }

    // 2. Handle relative imports
    else if (importPath.startsWith("./") || importPath.startsWith("../")) {
      const fileDir = path.dirname(filePath);
      resolved = path.join(fileDir, importPath);
    }

    // 3. Treat everything else as already root-relative
    else {
      resolved = path.join(rootDir, importPath);
    }

    // Normalize path
    resolved = path.normalize(resolved);

    // Remove extension
    resolved = resolved.replace(/\.[^/.]+$/, "");

    // Remove rootDir prefix if present
    if (rootDir && resolved.startsWith(rootDir)) {
      resolved = path.relative(rootDir, resolved);
    }

    // Convert to dot namespace
    return resolved.split(path.sep).join(".");
  }
  function serialize(node) {
    switch (node.kind) {
      case ts.SyntaxKind.ImportDeclaration:
        const importClause = node.importClause;
        return {
          path: node.moduleSpecifier.text,
          names: importClause && importClause.namedBindings && importClause.namedBindings.elements
            ? importClause.namedBindings.elements.map(e => e.name.text)
            : [],
          alias: importClause && importClause.name ? importClause.name.text : null,
          name: resolvePath(".", node.moduleSpecifier.text),
          is_relative: node.moduleSpecifier.text.startsWith(".")
        };
      case ts.SyntaxKind.FunctionDeclaration:
        return {
          name: node.name ? node.name.text : "<anonymous>",
          params: node.parameters.map(p => p.name.getText()),
          returns: node.type ? node.type.getText() : null,
          decorators: node.decorators ? node.decorators.map(d => d.getText()) : [],
          is_async: (getModifiers(node).includes("AsyncKeyword")),
          calls: [] // optional
        };
      case ts.SyntaxKind.ClassDeclaration:
        return {
          name: node.name ? node.name.text : "<anonymous>",
          bases: node.heritageClauses ? node.heritageClauses.flatMap(h => h.types.map(t => t.expression.getText())) : [],
          methods: node.members
            .filter(m => ts.isMethodDeclaration(m))
            .map(serialize),
          decorators: node.decorators ? node.decorators.map(d => d.getText()) : []
        };
      case ts.SyntaxKind.MethodDeclaration:
        return {
          name: node.name.getText(),
          params: node.parameters.map(p => p.name.getText()),
          returns: node.type ? node.type.getText() : null,
          decorators: node.decorators ? node.decorators.map(d => d.getText()) : [],
          is_async: (getModifiers(node).includes("AsyncKeyword")),
          calls: []
        };
      case ts.SyntaxKind.VariableStatement:
        return node.declarationList.declarations.map(d => ({
          name: d.name.getText(),
          type: "variable",
          is_public: true
        }));
      case ts.SyntaxKind.ExportDeclaration:
        return {
          name: node.exportClause ? node.exportClause.getText() : "*",
          type: "export",
          is_public: true
        };
      default:
        return null;
    }
  }

  // --- walk AST ---
  let ir = {
    path: filePath,
    name: formatPathToNamespace(filePath),
    imports: [],
    exports: [],
    functions: [],
    classes: [],
    has_main_guard: false
  };

  ts.forEachChild(sourceFile, node => {
    switch (node.kind) {
      case ts.SyntaxKind.ImportDeclaration:
        ir.imports.push(serialize(node));
        break;
      case ts.SyntaxKind.FunctionDeclaration:
        ir.functions.push(serialize(node));
        break;
      case ts.SyntaxKind.ClassDeclaration:
        ir.classes.push(serialize(node));
        break;
      case ts.SyntaxKind.VariableStatement:
        ir.exports.push(...serialize(node));
        break;
      case ts.SyntaxKind.ExportDeclaration:
        ir.exports.push(serialize(node));
        break;
      case ts.SyntaxKind.IfStatement:
        // crude main guard detection
        if (node.expression.getText() === "require.main === module") {
          ir.has_main_guard = true;
        }
        break;
    }
  });

  // --- output ---
  console.log(JSON.stringify(ir, null, 2));
})
