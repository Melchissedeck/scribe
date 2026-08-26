# Journal d'audit

Scribe journalise deux catégories d'événements dans la table `logs`, pour
répondre à l'exigence de traçabilité identifiée dans l'analyse RGPD du
dossier de cadrage :

- **`login`** : chaque connexion réussie (`POST /auth/login`).
- **`account_deletion`** : chaque suppression de compte
  (`DELETE /users/me`).

## Structure

| Champ     | Description                                                    |
|-----------|------------------------------------------------------------------|
| `action`  | Type d'événement (`login`, `account_deletion`).                 |
| `user_id` | Utilisateur concerné. Passe à `NULL` si le compte est ensuite supprimé (le log de suppression survit à la suppression elle-même). |
| `date`    | Horodatage UTC de l'événement.                                  |
| `detail`  | Contexte libre (l'email concerné, au moment de l'événement).    |

## Consultation

`GET /admin/logs` retourne l'ensemble du journal, trié du plus récent au
plus ancien. Route réservée à un usage interne : protégée par un en-tête
`X-Admin-Key`, comparé à la variable d'environnement `ADMIN_API_KEY`
(jamais par le token JWT d'un utilisateur classique). Sans cette variable
configurée côté serveur, la route refuse tout accès.

```bash
curl -H "X-Admin-Key: $ADMIN_API_KEY" https://<backend>/admin/logs
```

## Politique de rétention

- Les entrées sont conservées **12 mois glissants**, une durée jugée
  suffisante pour une analyse d'incident a posteriori sans constituer une
  conservation excessive au regard du RGPD (principe de minimisation).
- Aucune purge automatique n'est encore en place (hors périmètre de ce
  ticket) : une tâche planifiée supprimant les entrées de plus de 12 mois
  est identifiée comme suite logique, à traiter dans un sprint ultérieur.
- Le journal n'a pas vocation à être exhaustif (pas de journalisation de
  chaque appel API) : il se limite aux deux événements sensibles au sens
  RGPD listés ci-dessus.
