# 🏠 Gestion Locative

Application web de gestion locative : biens immobiliers, locataires, paiements et quittances.

## 🚀 Installation et lancement

### Prérequis : installer uv (une seule fois)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Lancer l'application

```bash
uvx --from git+https://github.com/darkxander/Gestion_Locative gestion-locative
```

La première fois, les dépendances sont téléchargées automatiquement (~30 secondes).
Le navigateur s'ouvre ensuite automatiquement. `Ctrl+C` pour arrêter.

## 🛠 Développement

```bash
git clone https://github.com/darkxander/Gestion_Locative
cd Gestion_Locative
pip install -e .
gestion-locative
```

## ✨ Fonctionnalités

- **Biens** : appartements, locaux commerciaux
- **Locataires** : informations, bail, historique
- **Paiements** : loyer, eau, ordures ménagères, taxe foncière
- **Quittances** : génération PDF imprimable
- **Statistiques** : revenus, taux d'occupation
- **Tableau de bord** : vue d'ensemble, alertes loyers en retard

## 💾 Données

Les données sont stockées localement :
- **macOS** : `~/Library/Application Support/GestionLocative/gestion_locative.db`
- **Linux** : `~/.config/gestion_locative/gestion_locative.db`

Rien n'est envoyé sur internet. Pour sauvegarder, copiez simplement ce fichier.

## 📝 Notes

- Fonctionne **entièrement en local**, aucune connexion internet requise après installation
- Compatible macOS et Linux

---

Développé avec ❤️ en Python/Flask
