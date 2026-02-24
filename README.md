# 🏠 Gestion Locative

Application de gestion locative pour un appartement et un local commercial.

## 📦 Installation

### Pour l'utilisateur (votre père)

1. **Téléchargez** le fichier `GestionLocative.dmg`
2. **Double-cliquez** dessus pour l'ouvrir
3. **Glissez** l'application `GestionLocative` dans le dossier `Applications`
4. **Lancez** l'application depuis le dossier Applications

⚠️ **Premier lancement sur Mac** : Si macOS affiche "L'application ne peut pas être ouverte", faites :
   - Clic droit sur l'application → "Ouvrir"
   - Cliquez sur "Ouvrir" dans la boîte de dialogue

### Pour le développeur

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python run.py
```

## 🚀 Utilisation

1. **Lancez** l'application
2. Votre navigateur s'ouvrira automatiquement sur `http://127.0.0.1:5000`
3. **Commencez** par remplir vos informations dans **Paramètres** (pour les quittances)
4. **Ajoutez** vos biens immobiliers
5. **Ajoutez** vos locataires
6. **Enregistrez** les paiements mensuels
7. **Générez** les quittances

## ✨ Fonctionnalités

- **Gestion des biens** : Appartement, local commercial
- **Gestion des locataires** : Informations, bail, historique
- **Suivi des paiements** : 
  - Loyer
  - Eau et assainissement
  - Ordures ménagères
  - Taxe foncière
- **Génération de quittances** : PDF imprimable avec tous les paiements du mois
- **Statistiques** : Revenus, taux d'occupation
- **Tableau de bord** : Vue d'ensemble, alertes loyers en retard

## 💾 Données

Les données sont stockées localement dans un fichier `gestion_locative.db`.
Ce fichier se trouve dans le même dossier que l'application.

**Sauvegarde** : Copiez simplement le fichier `gestion_locative.db` pour sauvegarder vos données.

## 🛠 Création du package

Pour créer un package à distribuer :

```bash
# Rendre le script exécutable
chmod +x build_package.sh

# Lancer la création du package
./build_package.sh
```

Le fichier `GestionLocative.dmg` sera créé dans le dossier `dist/`.

## 📝 Notes

- L'application fonctionne **entièrement en local**, aucune connexion internet n'est requise
- Compatible avec **macOS** (Intel et Apple Silicon)
- Les données restent sur votre ordinateur, rien n'est envoyé sur internet

---

Développé avec ❤️ en Python/Flask
