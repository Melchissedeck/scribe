# Modele de donnees Scribe

Ce document liste les tables de la base de donnees et leurs colonnes.
Chaque nouvelle table doit etre ajoutee ici au moment de sa creation.

## Table users

Represente une personne inscrite sur Scribe.

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| id | integer | primary key | Identifiant unique de l'utilisateur |
| name | varchar(100) | not null | Nom complet ou pseudonyme |
| email | varchar(150) | unique, not null | Adresse email, sert d'identifiant de connexion |
| hashed_password | varchar(255) | not null | Mot de passe hashe, jamais stocke en clair |
| created_at | datetime | not null | Date de creation du compte |

## Table recordings

Représente une session de captation lancée par un utilisateur (visioconference via Vexa).

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| id | integer | primary key | Identifiant unique de la session |
| user_id | integer | foreign key → users.id, not null | Utilisateur ayant lancé la session |
| platform | varchar(50) | not null | Plateforme visio : google_meet, zoom, teams |
| native_meeting_id | varchar(255) | not null | Identifiant natif de la réunion sur la plateforme |
| bot_name | varchar(100) | not null | Nom affiche par le bot dans la réunion |
| status | varchar(20) | not null | Etat de la session : pending, active, stopped, error |
| transcript | text | nullable | Transcription brute récupérée depuis Vexa |
| started_at | datetime | not null | Date de lancement de la session |
| stopped_at | datetime | nullable | Date d'arrêt de la session |
