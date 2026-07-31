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
