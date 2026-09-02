# Design system Scribe

Charte extraite de la maquette de référence (Scribe.html).
Toute nouvelle interface doit réutiliser ces tokens plutôt que définir de nouvelles valeurs.

## Couleurs

| Usage | Variable | Valeur |
|---|---|---|
| Primaire | --color-primary | #2563EB |
| Primaire clair | --color-primary-light | #3B82F6 |
| Texte principal | --color-text | #0F172A |
| Texte secondaire | --color-text-secondary | #475569 |
| Texte tertiaire | --color-text-muted | #64748B |
| Fond de page | --color-background | #F8FAFD |
| Fond de carte | --color-surface | #FFFFFF |
| Fond actif léger | --color-primary-bg | #EAF1FF |
| Bordure standard | --color-border | #E3E9F2 |
| Bordure accentuée | --color-border-primary | #D6E2FB |
| Succès | --color-success | #16A34A |
| Erreur | --color-error | #EF4444 |
| Avertissement | --color-warning | #D97706 |

## Typographie

- Police principale : Manrope (texte, titres, UI)
- Police secondaire : JetBrains Mono (donnees techniques : timestamps, ID, transcriptions brutes)
- Graisses : 800 (titres, labels forts), 700 (sous-titres, boutons), 600 (texte important)
- Tailles usuelles : de 9.5px (badges) a 18px (titres d'ecran), la majorite du texte UI entre 11px et 14px

## Formes

- Boutons et champs : border-radius 10px
- Cartes : border-radius 11px a 14px
- Badges et pills : border-radius 99px
- Avatars : border-radius 50%

## Ombres

- Carte au repos : 0 10px 30px rgba(15,23,42,.05)
- Bouton primaire : 0 4px 12px rgba(37,99,235,.18), 0 4px 12px rgba(37,99,235,.35) au survol

## Espacements

- Gaps entre elements : 6 a 12px
- Padding boutons : 9px 15px a 11px 17px
- Padding cartes : 18px 20px

## Stack frontend

HTML, CSS et JavaScript natifs, sans framework ni etape de build.
Chaque ecran est un fichier HTML dans frontend/pages, avec son propre module JS dans frontend/js.
Les appels au backend passent par fetch() vers l'API FastAPI.
