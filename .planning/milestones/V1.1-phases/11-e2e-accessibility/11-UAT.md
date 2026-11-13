---
status: complete
phase: 11-e2e-accessibility
source:
  - 11-01-SUMMARY.md
  - 11-02-SUMMARY.md
  - 11-03-SUMMARY.md
  - 11-04-SUMMARY.md
  - 11-05-SUMMARY.md
  - 11-06-SUMMARY.md
  - 11-07-SUMMARY.md
started: 2026-11-11T07:36:20Z
updated: 2026-11-11T20:09:32.603Z
---

## Current Test

[testing complete]

## Tests

### 1. Recherche en français
expected: Sur https://app.dev.letmegetin.org, sans cookie de langue : le titre, le champ de recherche, les filtres, les familles de handicap et le compteur de résultats sont en français. Le compteur se lit « N lieux » et la carte porte un libellé français.
result: pass

### 2. Bascule français / anglais
expected: Le sélecteur FR/EN change toute la page sans rechargement incohérent. En anglais, le compteur se lit « N places » et « 0 places » ; de retour en français, « 0 lieu » au singulier. Le choix survit à un rechargement et `<html lang>` suit la langue.
result: pass

### 3. Fiche lieu localisée
expected: Une fiche lieu affiche en français ses titres, la barre de complétion, l'arbre d'accessibilité, le formulaire de contribution et les dates d'avis. Après bascule en anglais, toute l'interface passe en anglais et les dates sont au format en-GB, sans texte français oublié.
result: pass
note: "Re-tested after the LET-83 fix was deployed to dev (b2c073b): 5/5 page loads 200, EN cookie renders lang=en and 'Reviews (0)'."
resolved_by: "LET-83 / PR #57"


### 4. Pages de connexion, inscription et vérification
expected: Les pages /login, /register et /verify affichent leurs titres, intros et messages d'attente dans la langue choisie. Après bascule en anglais puis rechargement, aucune phrase française ne subsiste dans l'interface.
result: pass

### 5. Compte connecté localisé
expected: Une fois connecté, /account affiche ses libellés et la bannière de vérification dans la langue courante. La bascule FR/EN met à jour la page et le rechargement conserve la langue.
result: pass

### 6. Contribution à une fiche
expected: Connecté avec le compte de test, ouvrir un lieu qui a des critères, modifier un critère et envoyer. Le message de succès est dans la langue courante, la valeur est enregistrée, et un rechargement montre la contribution sans erreur.
result: pass

### 7. Publication d'un avis
expected: Connecté, publier un avis avec une note et un texte. L'avis apparaît dans la liste avec la date formatée dans la langue courante. Un seul avis est créé par envoi, et un rechargement ne le duplique pas.
result: pass

### 8. Attribution MapLibre lisible
expected: Sur la page de recherche, le lien d'attribution MapLibre est souligné et reste distinguable autrement que par la couleur seule, conformément à WCAG 1.4.1.
result: pass

### 9. Parcours lecteur d'écran (VoiceOver / NVDA)
expected: Avec VoiceOver sur macOS ou NVDA sur Windows, parcourir la recherche, une fiche lieu et la connexion : chaque contrôle est annoncé avec son nom, son rôle et son état, l'ordre de focus est logique et aucun piège clavier ne bloque le parcours.
result: pass

### 10. Valeurs de contribution indépendantes de la langue (automatisé)
expected: Le formulaire envoie le slug d'option et oui/non, jamais le libellé affiché.
result: pass
source: automated
coverage_id: 11-05/D2

### 11. Dates d'avis localisées (automatisé)
expected: Les dates passent par formatDate(created, locale).
result: pass
source: automated
coverage_id: 11-05/D4

### 12. Bannière de vérification avec locale (automatisé)
expected: VerifyBanner reçoit une locale obligatoire depuis la page lieu.
result: pass
source: automated
coverage_id: 11-05/D5

### 13. Compte et bannière avec locale serveur (automatisé)
expected: La page compte résout la locale côté serveur et la transmet à AccountView puis VerifyBanner.
result: pass
source: automated
coverage_id: 11-06/D2

### 14. Garde i18n (automatisé)
expected: check:i18n passe sur l'arbre, échoue sur un littéral français réintroduit, et ignore un href="#avis".
result: pass
source: automated
coverage_id: 11-06/D3

## Summary

total: 14
passed: 14
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

```yaml
- gap_id: G-11-3
  truth: "Une fiche lieu affiche en français ses titres, la barre de complétion, l'arbre d'accessibilité, le formulaire de contribution et les dates d'avis. Après bascule en anglais, toute l'interface passe en anglais et les dates sont au format en-GB, sans texte français oublié."
  status: resolved
  reason: "User reported: erreur serveur"
  severity: blocker
  resolved_by: "LET-83 / PR #57 (b2c073b), deployed to dev"

  test: 3
  artifacts:
    - "web/src/lib/server-api.ts"
  missing:
    - "server-side renders were not forwarding x-forwarded-for / x-api-key (fix in PR #57, pending deploy)"
```
