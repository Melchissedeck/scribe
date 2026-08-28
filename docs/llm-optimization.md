# Optimisation des prompts LLM

## Contexte

Scribe fait trois types d'appels à l'API Anthropic par réunion :

| Appel | Méthode | Sortie |
|---|---|---|
| Résumé libre | `LLMService.generate_summary()` | Texte libre |
| Extraction structurée | `LLMService.generate_structured_summary()` | JSON (`StructuredSummary`, via *structured outputs*) |
| Classification par segment | `LLMService.classify_segments()` | JSON (`SegmentClassificationResult`, via *structured outputs*) |

Les deux derniers utilisent `output_config`/`output_format` : l'API contraint
déjà la sortie au schéma Pydantic déclaré, et ce schéma envoie ses propres
`description` de champ au modèle. Les prompts système d'origine réexpliquaient
en prose ce que le schéma dit déjà (« extrait les thèmes, les décisions, les
actions... ») — c'est la principale redondance identifiée et supprimée.

## Méthodologie de mesure

Un script de benchmark (non versionné, exécuté en local) appelle les 3
méthodes sur un jeu de 3 transcriptions de test représentatives — **courte**
(2 répliques), **moyenne** (point de sprint, ~150 mots), **longue** (réunion à
3 sujets avec plusieurs décisions et actions, ~400 mots) — une fois avec les
prompts d'origine, une fois avec les prompts optimisés. Pour chaque appel :

- `response.usage.input_tokens` / `output_tokens` : consommation réelle de
  l'appel complet (instructions + transcription).
- `client.messages.count_tokens()` sur les instructions seules (transcription
  vide) : isole le **coût fixe du prompt**, indépendant de la taille de la
  réunion — c'est le seul levier qu'une optimisation de prompt peut réduire
  (le contenu de la transcription, lui, ne se compresse pas sans perdre de
  l'information).

## Prompts avant / après

**`generate_summary`** — prompt utilisateur :

| Avant | Après |
|---|---|
| "Voici la transcription d'un enregistrement audio. Rédige un résumé clair et concis en texte libre, en français, qui reprend les points essentiels." | "Rédige un résumé clair et concis, en français, de cette transcription de réunion." |

**`generate_structured_summary`** — prompt système :

| Avant | Après |
|---|---|
| "Tu es un assistant qui génère des comptes-rendus de réunion. Extrait les thèmes abordés, les décisions prises et les actions à réaliser. Si une information n'est pas mentionnée dans la transcription, utilise une liste vide ou null. N'invente jamais d'information." | "Analyse cette transcription de réunion selon le schéma demandé. N'invente rien : liste vide ou null si une information est absente." |

**`classify_segments`** — prompt système :

| Avant | Après |
|---|---|
| "Tu es un assistant qui analyse des transcriptions de réunion. Pour CHAQUE segment numéroté ci-dessous, détermine son ton dominant, son thème principal et son niveau d'urgence. Réponds pour tous les segments, dans le même ordre, en reprenant l'index exact de chaque segment." | "Classe chaque segment numéroté ci-dessous selon le schéma demandé, dans le même ordre, en conservant son index exact." |

Ce qui a été retiré dans les deux prompts système structurés est exactement ce
que `Field(description=...)` sur `StructuredSummary` / `SegmentClassification`
(`app/schemas/llm_summary.py`) dit déjà au modèle via le schéma JSON envoyé
avec `output_format`.

## Résultats mesurés

### Coût fixe du prompt (instructions seules, transcription vide)

| Appel | Avant | Après | Gain |
|---|---:|---:|---:|
| `generate_summary` | 64 tokens | 40 tokens | **-37 %** |
| `generate_structured_summary` | 115 tokens | 61 tokens | **-47 %** |
| `classify_segments` | 125 tokens | 61 tokens | **-51 %** |
| **Total (3 appels)** | **304** | **162** | **-46,7 %** |

C'est le gain réel et reproductible de cette optimisation : indépendant de la
taille de la réunion, il s'applique à *chaque* appel.

### Consommation totale mesurée (9 appels : 3 types × 3 tailles de transcription)

| | Avant | Après | Delta |
|---|---:|---:|---:|
| Tokens d'entrée (input) | 8 427 | 8 001 | **-426 (-5,1 %)** |
| Tokens de sortie (output) | 2 838 | 2 713 | -125 (-4,4 %, bruit de génération — voir Limites) |

Le gain relatif sur le total d'entrée est plus faible que sur le coût fixe
seul, car la transcription elle-même (non compressible) domine le volume de
tokens dès que la réunion dépasse quelques répliques — voir le détail par
appel :

| Appel | Taille | Input avant | Input après | Delta |
|---|---|---:|---:|---:|
| `generate_summary` | courte | 108 | 84 | -24 |
| `generate_summary` | moyenne | 337 | 313 | -24 |
| `generate_summary` | longue | 641 | 617 | -24 |
| `generate_structured_summary` | courte | 1 022 | 968 | -54 |
| `generate_structured_summary` | moyenne | 1 251 | 1 197 | -54 |
| `generate_structured_summary` | longue | 1 555 | 1 501 | -54 |
| `classify_segments` | courte | 895 | 831 | -64 |
| `classify_segments` | moyenne | 1 142 | 1 078 | -64 |
| `classify_segments` | longue | 1 476 | 1 412 | -64 |

Le delta par appel est constant (24/54/64 tokens) quelle que soit la taille de
la réunion : c'est exactement le coût fixe du prompt mesuré plus haut,
confirmant que la totalité du gain vient bien de la réduction de verbosité,
pas d'un effet de bord sur le traitement de la transcription.

## Qualité : avant / après

Comparaison manuelle des sorties sur les 9 appels du jeu de test :

- **`generate_structured_summary`** : mêmes thèmes identifiés, même nombre de
  décisions et d'actions sur les 3 transcriptions, formulations quasi
  identiques (ex. réunion longue : 3 thèmes / 4 décisions / 5 actions avant
  *et* après, contenu équivalent).
- **`classify_segments`** : même nombre de segments classifiés (2/8/18 selon
  la taille), tons et niveaux d'urgence identiques sur l'échantillon vérifié.
- **`generate_summary`** : mêmes points clés couverts dans les deux versions
  (mise en forme légèrement différente d'un essai à l'autre, comme c'est déjà
  le cas d'un appel à l'autre avec le prompt d'origine — texte libre, non
  contraint par un schéma).

Aucune perte de précision ou d'information constatée sur le jeu de test.

## Gains de coût chiffrés

Tarifs Claude Sonnet 5 : **2,00 $ / 1M tokens en entrée**, **10,00 $ / 1M en
sortie**.

Le gain déterministe est de **142 tokens d'entrée économisés par réunion
traitée** (24 + 54 + 64, les 3 appels confondus), soit **0,000284 $/réunion**
(2,84 × 10⁻⁴ $). Sur une base d'usage hypothétique de 500 réunions/mois :
**~0,14 $/mois** économisés sur le coût des instructions.

**En clair : l'impact en dollars est négligeable en valeur absolue.** Le
tarif d'entrée de Claude Sonnet 5 est déjà bas (2 $/1M tokens), et la
transcription — non compressible sans perte d'information — domine largement
le volume de tokens par appel dès que la réunion dépasse quelques échanges.
La vraie valeur de cette optimisation est la réduction de **46,7 % du coût
fixe par appel** (charge que l'app paie même sur les réunions les plus
courtes) et l'élimination d'une redondance de fond : les prompts système ne
répètent plus en prose ce que le schéma `output_format` communique déjà.

## Limites

- Jeu de test volontairement restreint (3 transcriptions synthétiques) —
  suffisant pour valider l'équivalence de comportement, pas un audit
  statistique de variance de sortie.
- La comparaison des tokens de sortie observe une baisse de 4,4 %, mais elle
  n'est pas attribuable à l'optimisation du prompt système : la longueur de
  sortie d'un texte libre ou d'un JSON à schéma fixe varie naturellement d'un
  appel à l'autre. Seule la mesure des tokens d'entrée (déterministe) est
  attribuée au changement de prompt.
- Si une réduction de coût plus significative est recherchée, le levier
  pertinent n'est pas la verbosité des instructions (déjà marginale) mais la
  taille des transcriptions envoyées telles quelles, ou `max_tokens` sur les
  réunions à très nombreux segments (`classify_segments` scale linéairement
  avec le nombre de segments).
