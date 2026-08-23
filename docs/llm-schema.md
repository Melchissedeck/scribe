# Schéma JSON du compte-rendu structuré (LLM)

## Contexte

`LLMService.generate_structured_summary()` génère un compte-rendu de réunion
structuré en JSON à partir d'une transcription, via l'API TogetherAI.

Contrairement à `generate_summary()` (texte libre), cette méthode impose au
LLM un format de sortie strict, validé côté serveur, avec une nouvelle
tentative automatique si le JSON retourné est invalide ou mal formé.

## Schéma attendu

```json
{
  "themes": ["string", "..."],
  "decisions": ["string", "..."],
  "actions": [
    {
      "description": "string",
      "responsable": "string ou null",
      "echeance": "string ou null"
    }
  ]
}
```

### Champs

| Champ | Type | Description |
|---|---|---|
| `themes` | `string[]` | Sujets principaux abordés pendant la réunion |
| `decisions` | `string[]` | Décisions prises pendant la réunion |
| `actions` | `ActionItem[]` | Actions à réaliser suite à la réunion |
| `actions[].description` | `string` | Ce qui doit être fait (obligatoire) |
| `actions[].responsable` | `string \| null` | Personne en charge, si mentionnée |
| `actions[].echeance` | `string \| null` | Échéance, si mentionnée (texte libre) |

Si une information n'est pas présente dans la transcription, le LLM doit
retourner une liste vide (`[]`) ou `null`, jamais inventer de valeur.

## Exemple

```json
{
  "themes": ["Sprint review", "Intégration TogetherAI"],
  "decisions": ["Merger la PR du dashboard avant vendredi"],
  "actions": [
    {
      "description": "Ajouter des crédits sur le compte TogetherAI",
      "responsable": "Priscilia",
      "echeance": "vendredi"
    },
    {
      "description": "Revoir la PR structured-summary-json",
      "responsable": null,
      "echeance": null
    }
  ]
}
```

## Validation et gestion des erreurs

1. Le prompt système impose explicitement le format JSON, sans texte
   d'accompagnement ni balises markdown.
2. La réponse brute du LLM est nettoyée (retrait d'éventuelles balises
```json ... ```), puis parsée avec `json.loads`.
3. Le JSON parsé est validé contre le modèle Pydantic `StructuredSummary`
   (`app/schemas/llm_summary.py`).
4. Si le parsing ou la validation échoue, une nouvelle tentative est
   automatiquement effectuée (2 tentatives au total par défaut,
   configurable via le paramètre `max_attempts`).
5. Si toutes les tentatives échouent, la méthode retourne `None` — elle ne
   lève jamais d'exception, pour ne pas faire planter l'application
   appelante.

## Modèles Pydantic

Définis dans `backend/app/schemas/llm_summary.py` :

- `ActionItem` : `description`, `responsable` (optionnel), `echeance` (optionnel)
- `StructuredSummary` : `themes`, `decisions`, `actions`
```

Crée le fichier avec ce contenu, sauvegarde, puis committe :

```bash
git add docs/llm-schema.md
git commit -m "docs: document structured summary JSON schema"
```

Colle-moi le résultat.