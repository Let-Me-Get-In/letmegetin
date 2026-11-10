// Guard against French interface literals creeping back into the localized tree.
//
// The French copy lives in `src/lib/i18n.ts` and nowhere else. This script walks
// the AST of every swept source file and flags any string literal that looks
// French, wherever it sits: JSX text, JSX-expression literals
// (`{place.category ?? "Catégorie inconnue"}`), call arguments
// (`setGeoMessage("Localisation refusée …")`) and `.catch` bodies. A JSX-text-only
// scan would prove nothing here: the real French in this codebase lives in
// expressions and call arguments.
//
// Not scanned, by design:
//   - `href`, `className`, `id`, `key`, `value`, `type`, `role`, `name`, `htmlFor`
//     and `data-*` values: not display copy. This is why `#avis` in
//     `review-list.tsx` (`href={`/places/${slug}?page=…}#avis`}`) is not flagged.
//   - `*.test.*` / `*.spec.*` files.
//   - the `metadata` / `generateMetadata` export: SEO and brand titles.
//   - the key argument of `t()` / `tPlural()`: a dictionary identifier, not copy.
//
// No dependency: `typescript` is already a dev dependency of the web project.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const SCAN_ROOTS = [
  "src/components/search",
  "src/components/record",
  "src/components/auth",
  "src/components/account",
  "src/app/(auth)",
  "src/app/account",
  "src/app/page.tsx",
  "src/app/places/[slug]/page.tsx",
  "src/app/places/[slug]/not-found.tsx",
  "src/components/site-header.tsx",
  "src/components/locale-switch.tsx",
  "src/components/landing",
  "src/app/landing",
];

const EXCLUDED_ATTRS = new Set([
  "href",
  "className",
  "id",
  "key",
  "value",
  "type",
  "role",
  "name",
  "htmlFor",
  // Not `aria-label`: that one *is* copy and is scanned. `aria-labelledby` holds
  // element ids (`aria-labelledby="avis"`), like `id`.
  "aria-labelledby",
]);

const DENYLIST = [
  "Rechercher",
  "Recherche",
  "Résultats",
  "Chargement",
  "Autour de",
  "Localisation",
  "Aucun",
  "lieu",
  "Doublon",
  "Catégorie",
  "Enregistrer",
  "Publier",
  "Anonyme",
  "Précédent",
  "Suivant",
  "avis",
  "Note",
  "Photos",
  "Accessibilité",
  "Compléter",
  "Source non",
  "Non renseigné",
  "Se connecter",
  "Connectez-vous",
  "Mot de passe",
  "Créer un compte",
  "Mon compte",
  "Se déconnecter",
  "Réinitialiser",
  "Voir plus",
  "Vérifiez",
];

const FRENCH_CHARS = /[àâäéèêëîïôöùûüçœæÀÂÄÉÈÊËÎÏÔÖÙÛÜÇŒÆ]/;
const NOT_SCANNED_FILE = /\.(test|spec)\./;

function isExcludedName(name) {
  return EXCLUDED_ATTRS.has(name) || name.startsWith("data-");
}

function nodeName(node) {
  if (!node) return null;
  if (ts.isIdentifier(node)) return node.text;
  if (ts.isStringLiteral(node)) return node.text;
  return null;
}

// `export const metadata = …` and `export function generateMetadata() { … }`
function isMetadataDeclaration(node) {
  if (ts.isVariableStatement(node)) {
    return node.declarationList.declarations.some((declaration) => {
      const name = nodeName(declaration.name);
      return name === "metadata" || name === "generateMetadata";
    });
  }
  if (ts.isFunctionDeclaration(node)) {
    const name = nodeName(node.name);
    return name === "generateMetadata" || name === "metadata";
  }
  return false;
}

function collectFiles(entry, found) {
  const absolute = path.join(WEB_ROOT, entry);
  if (!fs.existsSync(absolute)) {
    // Fail fast: a stale path here would silently shrink the guard's coverage.
    throw new Error(`check:i18n: scan root does not exist: ${entry}`);
  }
  if (fs.statSync(absolute).isFile()) {
    if (/\.(ts|tsx)$/.test(absolute) && !NOT_SCANNED_FILE.test(absolute)) found.push(absolute);
    return;
  }
  for (const name of fs.readdirSync(absolute).sort()) {
    collectFiles(path.relative(WEB_ROOT, path.join(absolute, name)), found);
  }
}

// True when the literal is copy the reader sees. Everything that is not a
// non-display attribute/property, a `t()` key or inside `metadata` is copy.
function isDisplayLiteral(node) {
  let child = node;
  let current = node.parent;
  while (current) {
    if (ts.isJsxAttribute(current)) {
      return !isExcludedName(nodeName(current.name) ?? "");
    }
    if (ts.isPropertyAssignment(current)) {
      const name = nodeName(current.name);
      if (name !== null && isExcludedName(name)) return false;
    }
    if (ts.isCallExpression(current)) {
      const index = current.arguments.indexOf(child);
      if (index === 1) {
        const callee = nodeName(current.expression);
        if (callee === "t" || callee === "tPlural") return false;
      }
      if (index !== -1) return true;
    }
    child = current;
    current = current.parent;
  }
  return true;
}

function looksFrench(text) {
  if (FRENCH_CHARS.test(text)) return true;
  const lower = text.toLowerCase();
  return DENYLIST.some((token) => lower.includes(token.toLowerCase()));
}

function scanFile(absolute, hits) {
  const source = fs.readFileSync(absolute, "utf8");
  const sourceFile = ts.createSourceFile(
    absolute,
    source,
    ts.ScriptTarget.Latest,
    true,
    absolute.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );

  function visit(node) {
    if (isMetadataDeclaration(node)) return;
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      if (isDisplayLiteral(node) && looksFrench(node.text)) {
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
        hits.push({
          file: path.relative(WEB_ROOT, absolute),
          line: line + 1,
          text: node.text,
        });
      }
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
}

const files = [];
for (const root of SCAN_ROOTS) collectFiles(root, files);

const hits = [];
for (const file of files) scanFile(file, hits);

if (hits.length > 0) {
  for (const hit of hits) {
    process.stderr.write(`${hit.file}:${hit.line}  ${JSON.stringify(hit.text)}\n`);
  }
  process.stderr.write(
    `check:i18n: ${hits.length} French literal(s) in ${files.length} scanned file(s). ` +
      `Move them to src/lib/i18n.ts and render them with t().\n`,
  );
  process.exit(1);
}

process.stdout.write(`check:i18n: ${files.length} files scanned, no French literal.\n`);
