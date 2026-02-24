"""
Système de Gestion Locative
Application Flask pour gérer la location d'un appartement et d'un local commercial
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pathlib import Path
import secrets
import sys
import os

db = SQLAlchemy()

# ==================== CONSTANTES ====================

CATEGORIES_PAIEMENT = [
    ('loyer', 'Loyer'),
    ('eau_assainissement', 'Eau et assainissement'),
    ('ordures_menageres', 'Ordures ménagères'),
    ('taxe_fonciere', 'Taxe foncière'),
]

MOIS_NOMS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
             'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

MOIS_NOMS_COURTS = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                     'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

# ==================== HELPERS ====================


def _get_data_dir():
    """Répertoire de données utilisateur (base de données)."""
    if sys.platform == 'darwin':
        data_dir = os.path.join(
            os.path.expanduser('~'),
            'Library', 'Application Support', 'GestionLocative'
        )
    else:
        data_dir = os.path.join(
            os.path.expanduser('~'),
            '.config', 'gestion_locative'
        )
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _safe_float(value, default=None):
    if not value:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=None):
    if not value:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_date(value, fmt='%Y-%m-%d'):
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except (ValueError, TypeError):
        return None


def _parse_bien_form(form):
    return {
        'nom': form.get('nom', '').strip(),
        'type_bien': form.get('type_bien', ''),
        'adresse': form.get('adresse', '').strip(),
        'surface': _safe_float(form.get('surface')),
        'description': form.get('description', ''),
        'charges_mensuelles': _safe_float(form.get('charges_mensuelles'), 0),
        'date_acquisition': _safe_date(form.get('date_acquisition')),
    }


def _parse_locataire_form(form):
    return {
        'nom': form.get('nom', '').strip(),
        'prenom': form.get('prenom', '').strip() or None,
        'email': form.get('email', ''),
        'telephone': form.get('telephone', ''),
        'date_naissance': _safe_date(form.get('date_naissance')),
        'raison_sociale': form.get('raison_sociale', '').strip() or None,
        'siret': form.get('siret', '').strip() or None,
        'dirigeant': form.get('dirigeant', '').strip() or None,
        'bien_id': _safe_int(form.get('bien_id')),
        'date_debut_bail': _safe_date(form.get('date_debut_bail')),
        'date_fin_bail': _safe_date(form.get('date_fin_bail')),
        'loyer_mensuel': _safe_float(form.get('loyer_mensuel')),
        'depot_garantie': _safe_float(form.get('depot_garantie'), 0),
        'jour_paiement': _safe_int(form.get('jour_paiement'), 1),
    }


def _validate_locataire_data(data):
    if not data['bien_id']:
        return 'Veuillez sélectionner un bien.'

    # Déterminer le type de bien pour adapter la validation
    bien = Bien.query.get(data['bien_id'])
    if not bien:
        return 'Le bien sélectionné est introuvable.'

    if bien.type_bien == 'local_commercial':
        # Validation locataire professionnel
        if not data.get('raison_sociale'):
            return 'La raison sociale est obligatoire pour un local commercial.'
        if not data.get('siret'):
            return 'Le numéro SIRET est obligatoire pour un local commercial.'
        if len(data['siret']) != 14 or not data['siret'].isdigit():
            return 'Le numéro SIRET doit contenir exactement 14 chiffres.'
    else:
        # Validation locataire particulier
        if not data['nom'] or not data.get('prenom'):
            return 'Le nom et le prénom sont obligatoires.'

    if not data['date_debut_bail']:
        return 'La date de début de bail est obligatoire.'
    if data['loyer_mensuel'] is None or data['loyer_mensuel'] < 0:
        return 'Le loyer mensuel doit être un nombre positif.'
    if data['depot_garantie'] is not None and data['depot_garantie'] < 0:
        return 'Le dépôt de garantie ne peut pas être négatif.'
    if data['jour_paiement'] is not None and (data['jour_paiement'] < 1 or data['jour_paiement'] > 28):
        return 'Le jour de paiement doit être entre 1 et 28.'
    if data['date_fin_bail'] and data['date_debut_bail'] and data['date_fin_bail'] < data['date_debut_bail']:
        return 'La date de fin de bail doit être postérieure à la date de début.'
    return None


def _parse_paiement_form(form):
    return {
        'locataire_id': _safe_int(form.get('locataire_id')),
        'montant': _safe_float(form.get('montant')),
        'date_paiement': _safe_date(form.get('date_paiement')),
        'mois_concerne': form.get('mois_concerne', ''),
        'categorie': form.get('categorie', 'loyer'),
        'mode_paiement': form.get('mode_paiement', ''),
        'commentaire': form.get('commentaire', ''),
    }


def _validate_paiement_data(data):
    if not data['locataire_id']:
        return 'Veuillez sélectionner un locataire.'
    if data['montant'] is None or data['montant'] <= 0:
        return 'Le montant doit être un nombre positif.'
    if not data['date_paiement']:
        return 'La date de paiement est obligatoire.'
    if not data['mois_concerne']:
        return 'Le mois concerné est obligatoire.'
    return None


# ==================== MODÈLES ====================

class Bien(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type_bien = db.Column(db.String(50), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    surface = db.Column(db.Float)
    description = db.Column(db.Text)
    charges_mensuelles = db.Column(db.Float, default=0)
    date_acquisition = db.Column(db.Date)

    locataires = db.relationship('Locataire', backref='bien', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Bien {self.nom}>'

    @property
    def locataire_actuel(self):
        for loc in self.locataires:
            if loc.actif:
                return loc
        return None


class Locataire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    date_naissance = db.Column(db.Date)

    # Champs spécifiques locataire professionnel (local commercial)
    raison_sociale = db.Column(db.String(200))
    siret = db.Column(db.String(14))
    dirigeant = db.Column(db.String(200))

    bien_id = db.Column(db.Integer, db.ForeignKey('bien.id'), nullable=False)
    date_debut_bail = db.Column(db.Date, nullable=False)
    date_fin_bail = db.Column(db.Date)
    loyer_mensuel = db.Column(db.Float, nullable=False)
    depot_garantie = db.Column(db.Float, default=0)
    jour_paiement = db.Column(db.Integer, default=1)
    actif = db.Column(db.Boolean, default=True)

    paiements = db.relationship('Paiement', backref='locataire', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        if self.raison_sociale:
            return f'<Locataire {self.raison_sociale}>'
        return f'<Locataire {self.prenom} {self.nom}>'

    @property
    def nom_complet(self):
        if self.raison_sociale:
            return self.raison_sociale
        return f'{self.prenom} {self.nom}'

    @property
    def est_professionnel(self):
        return bool(self.raison_sociale)

    @property
    def loyer_total(self):
        charges = self.bien.charges_mensuelles if self.bien else 0
        return self.loyer_mensuel + charges


class Bailleur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    adresse = db.Column(db.String(500), nullable=False)
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    siret = db.Column(db.String(20))

    def __repr__(self):
        return f'<Bailleur {self.nom}>'

    @property
    def adresse_complete(self):
        adresse = self.adresse
        if self.code_postal and self.ville:
            adresse += f', {self.code_postal} {self.ville}'
        return adresse


class Paiement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    locataire_id = db.Column(db.Integer, db.ForeignKey('locataire.id'), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    date_paiement = db.Column(db.Date, nullable=False)
    mois_concerne = db.Column(db.String(7), nullable=False)
    categorie = db.Column(db.String(50), nullable=False, default='loyer')
    mode_paiement = db.Column(db.String(50))
    commentaire = db.Column(db.Text)
    quittance_generee = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Paiement {self.montant}€ - {self.categorie} - {self.mois_concerne}>'

    @property
    def categorie_label(self):
        labels = dict(CATEGORIES_PAIEMENT)
        return labels.get(self.categorie, self.categorie)


# ==================== APPLICATION FACTORY ====================

def create_app():
    """Crée et configure l'application Flask."""
    template_folder = str(Path(__file__).parent / 'templates')
    data_dir = _get_data_dir()
    db_path = os.path.join(data_dir, 'gestion_locative.db')

    app = Flask(__name__, template_folder=template_folder)
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    _register_routes(app)
    return app


def _register_routes(app):
    """Enregistre toutes les routes sur l'application."""

    # ==================== ROUTES PRINCIPALES ====================

    @app.route('/')
    def index():
        biens = Bien.query.all()
        locataires_actifs = Locataire.query.filter_by(actif=True).options(
            joinedload(Locataire.bien),
            joinedload(Locataire.paiements)
        ).all()

        revenus_mensuels = sum(loc.loyer_total for loc in locataires_actifs)

        mois_actuel = date.today().strftime('%Y-%m')
        paiements_mois = Paiement.query.filter_by(mois_concerne=mois_actuel).all()
        total_percu = sum(p.montant for p in paiements_mois)

        loyers_en_retard = []
        for loc in locataires_actifs:
            if not any(p.mois_concerne == mois_actuel for p in loc.paiements):
                if date.today().day > loc.jour_paiement:
                    loyers_en_retard.append(loc)

        return render_template('index.html',
                             biens=biens,
                             locataires_actifs=locataires_actifs,
                             revenus_mensuels=revenus_mensuels,
                             total_percu=total_percu,
                             loyers_en_retard=loyers_en_retard,
                             mois_actuel=mois_actuel)

    # ==================== ROUTES BIENS ====================

    @app.route('/biens')
    def liste_biens():
        biens = Bien.query.all()
        return render_template('biens/liste.html', biens=biens)

    @app.route('/biens/ajouter', methods=['GET', 'POST'])
    def ajouter_bien():
        if request.method == 'POST':
            data = _parse_bien_form(request.form)
            if not data['nom']:
                flash('Le nom du bien est obligatoire.', 'danger')
                return render_template('biens/formulaire.html', bien=None)
            if not data['adresse']:
                flash("L'adresse est obligatoire.", 'danger')
                return render_template('biens/formulaire.html', bien=None)
            if data['charges_mensuelles'] is not None and data['charges_mensuelles'] < 0:
                flash('Les charges mensuelles ne peuvent pas être négatives.', 'danger')
                return render_template('biens/formulaire.html', bien=None)
            try:
                bien = Bien(**data)
                db.session.add(bien)
                db.session.commit()
                flash('Bien ajouté avec succès !', 'success')
                return redirect(url_for('liste_biens'))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('biens/formulaire.html', bien=None)
        return render_template('biens/formulaire.html', bien=None)

    @app.route('/biens/<int:id>')
    def detail_bien(id):
        bien = Bien.query.get_or_404(id)
        return render_template('biens/detail.html', bien=bien)

    @app.route('/biens/<int:id>/modifier', methods=['GET', 'POST'])
    def modifier_bien(id):
        bien = Bien.query.get_or_404(id)
        if request.method == 'POST':
            data = _parse_bien_form(request.form)
            if not data['nom']:
                flash('Le nom du bien est obligatoire.', 'danger')
                return render_template('biens/formulaire.html', bien=bien)
            if not data['adresse']:
                flash("L'adresse est obligatoire.", 'danger')
                return render_template('biens/formulaire.html', bien=bien)
            if data['charges_mensuelles'] is not None and data['charges_mensuelles'] < 0:
                flash('Les charges mensuelles ne peuvent pas être négatives.', 'danger')
                return render_template('biens/formulaire.html', bien=bien)
            try:
                for key, value in data.items():
                    setattr(bien, key, value)
                db.session.commit()
                flash('Bien modifié avec succès !', 'success')
                return redirect(url_for('detail_bien', id=id))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('biens/formulaire.html', bien=bien)
        return render_template('biens/formulaire.html', bien=bien)

    @app.route('/biens/<int:id>/supprimer', methods=['POST'])
    def supprimer_bien(id):
        bien = Bien.query.get_or_404(id)
        try:
            db.session.delete(bien)
            db.session.commit()
            flash('Bien supprimé avec succès !', 'success')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de la suppression du bien.', 'danger')
        return redirect(url_for('liste_biens'))

    # ==================== ROUTES LOCATAIRES ====================

    @app.route('/locataires')
    def liste_locataires():
        locataires = Locataire.query.all()
        return render_template('locataires/liste.html', locataires=locataires)

    @app.route('/locataires/ajouter', methods=['GET', 'POST'])
    def ajouter_locataire():
        biens = Bien.query.all()
        if request.method == 'POST':
            data = _parse_locataire_form(request.form)
            erreur = _validate_locataire_data(data)
            if erreur:
                flash(erreur, 'danger')
                return render_template('locataires/formulaire.html', locataire=None, biens=biens)
            try:
                locataire = Locataire(**data, actif=True)
                db.session.add(locataire)
                db.session.commit()
                flash('Locataire ajouté avec succès !', 'success')
                return redirect(url_for('liste_locataires'))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('locataires/formulaire.html', locataire=None, biens=biens)
        return render_template('locataires/formulaire.html', locataire=None, biens=biens)

    @app.route('/locataires/<int:id>')
    def detail_locataire(id):
        locataire = Locataire.query.get_or_404(id)
        paiements = Paiement.query.filter_by(locataire_id=id).order_by(Paiement.date_paiement.desc()).all()
        return render_template('locataires/detail.html', locataire=locataire, paiements=paiements)

    @app.route('/locataires/<int:id>/modifier', methods=['GET', 'POST'])
    def modifier_locataire(id):
        locataire = Locataire.query.get_or_404(id)
        biens = Bien.query.all()
        if request.method == 'POST':
            data = _parse_locataire_form(request.form)
            erreur = _validate_locataire_data(data)
            if erreur:
                flash(erreur, 'danger')
                return render_template('locataires/formulaire.html', locataire=locataire, biens=biens)
            try:
                for key, value in data.items():
                    setattr(locataire, key, value)
                locataire.actif = 'actif' in request.form
                db.session.commit()
                flash('Locataire modifié avec succès !', 'success')
                return redirect(url_for('detail_locataire', id=id))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('locataires/formulaire.html', locataire=locataire, biens=biens)
        return render_template('locataires/formulaire.html', locataire=locataire, biens=biens)

    @app.route('/locataires/<int:id>/supprimer', methods=['POST'])
    def supprimer_locataire(id):
        locataire = Locataire.query.get_or_404(id)
        try:
            db.session.delete(locataire)
            db.session.commit()
            flash('Locataire supprimé avec succès !', 'success')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de la suppression du locataire.', 'danger')
        return redirect(url_for('liste_locataires'))

    # ==================== ROUTES PAIEMENTS ====================

    @app.route('/paiements')
    def liste_paiements():
        paiements = Paiement.query.order_by(Paiement.date_paiement.desc()).all()
        return render_template('paiements/liste.html', paiements=paiements)

    @app.route('/paiements/ajouter', methods=['GET', 'POST'])
    def ajouter_paiement():
        locataires = Locataire.query.filter_by(actif=True).all()
        if request.method == 'POST':
            data = _parse_paiement_form(request.form)
            erreur = _validate_paiement_data(data)
            if erreur:
                flash(erreur, 'danger')
                return render_template('paiements/formulaire.html', paiement=None, locataires=locataires, categories=CATEGORIES_PAIEMENT)
            try:
                paiement = Paiement(**data)
                db.session.add(paiement)
                db.session.commit()
                flash('Paiement enregistré avec succès !', 'success')
                return redirect(url_for('liste_paiements'))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('paiements/formulaire.html', paiement=None, locataires=locataires, categories=CATEGORIES_PAIEMENT)
        return render_template('paiements/formulaire.html', paiement=None, locataires=locataires, categories=CATEGORIES_PAIEMENT)

    @app.route('/paiements/<int:id>/modifier', methods=['GET', 'POST'])
    def modifier_paiement(id):
        paiement = Paiement.query.get_or_404(id)
        locataires = Locataire.query.filter_by(actif=True).all()
        if request.method == 'POST':
            data = _parse_paiement_form(request.form)
            erreur = _validate_paiement_data(data)
            if erreur:
                flash(erreur, 'danger')
                return render_template('paiements/formulaire.html', paiement=paiement, locataires=locataires, categories=CATEGORIES_PAIEMENT)
            try:
                for key, value in data.items():
                    setattr(paiement, key, value)
                db.session.commit()
                flash('Paiement modifié avec succès !', 'success')
                return redirect(url_for('liste_paiements'))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement. Vérifiez les données saisies.", 'danger')
                return render_template('paiements/formulaire.html', paiement=paiement, locataires=locataires, categories=CATEGORIES_PAIEMENT)
        return render_template('paiements/formulaire.html', paiement=paiement, locataires=locataires, categories=CATEGORIES_PAIEMENT)

    @app.route('/paiements/<int:id>/supprimer', methods=['POST'])
    def supprimer_paiement(id):
        paiement = Paiement.query.get_or_404(id)
        try:
            db.session.delete(paiement)
            db.session.commit()
            flash('Paiement supprimé avec succès !', 'success')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de la suppression du paiement.', 'danger')
        return redirect(url_for('liste_paiements'))

    # ==================== ROUTES QUITTANCES ====================

    @app.route('/quittances')
    def liste_quittances():
        locataires = Locataire.query.filter_by(actif=True).all()
        now = date.today().strftime('%Y-%m')
        return render_template('quittances/liste.html', locataires=locataires, now=now)

    @app.route('/quittances/generer/<int:locataire_id>/<mois>')
    def generer_quittance(locataire_id, mois):
        locataire = Locataire.query.get_or_404(locataire_id)

        try:
            parts = mois.split('-')
            if len(parts) != 2:
                raise ValueError
            annee = parts[0]
            mois_num = int(parts[1])
            int(annee)
            if mois_num < 1 or mois_num > 12:
                raise ValueError
        except (ValueError, AttributeError):
            flash('Format de mois invalide.', 'danger')
            return redirect(url_for('liste_quittances'))

        bailleur = Bailleur.query.first()
        paiements = Paiement.query.filter_by(locataire_id=locataire_id, mois_concerne=mois).all()

        paiements_par_categorie = {}
        for p in paiements:
            if p.categorie not in paiements_par_categorie:
                paiements_par_categorie[p.categorie] = []
            paiements_par_categorie[p.categorie].append(p)

        total_paiements = sum(p.montant for p in paiements)
        mois_nom = MOIS_NOMS[mois_num]

        return render_template('quittances/quittance.html',
                             locataire=locataire,
                             bailleur=bailleur,
                             paiements=paiements,
                             paiements_par_categorie=paiements_par_categorie,
                             total_paiements=total_paiements,
                             categories_labels=dict(CATEGORIES_PAIEMENT),
                             mois=mois,
                             mois_nom=mois_nom,
                             annee=annee,
                             date_generation=date.today())

    # ==================== ROUTES PARAMÈTRES ====================

    @app.route('/parametres', methods=['GET', 'POST'])
    def parametres():
        bailleur = Bailleur.query.first()
        if request.method == 'POST':
            try:
                nom = request.form.get('nom', '').strip()
                adresse = request.form.get('adresse', '').strip()
                if not nom or not adresse:
                    flash('Le nom et l\'adresse sont obligatoires.', 'danger')
                    return render_template('parametres.html', bailleur=bailleur)

                fields = {
                    'nom': nom,
                    'adresse': adresse,
                    'code_postal': request.form.get('code_postal', ''),
                    'ville': request.form.get('ville', ''),
                    'telephone': request.form.get('telephone', ''),
                    'email': request.form.get('email', ''),
                    'siret': request.form.get('siret', ''),
                }

                if bailleur:
                    for key, value in fields.items():
                        setattr(bailleur, key, value)
                else:
                    bailleur = Bailleur(**fields)
                    db.session.add(bailleur)

                db.session.commit()
                flash('Paramètres enregistrés avec succès !', 'success')
                return redirect(url_for('parametres'))
            except Exception:
                db.session.rollback()
                flash("Erreur lors de l'enregistrement des paramètres.", 'danger')
        return render_template('parametres.html', bailleur=bailleur)

    # ==================== ROUTES STATISTIQUES ====================

    @app.route('/statistiques')
    def statistiques():
        date_courante = date.today()

        date_12_mois = date_courante - relativedelta(months=12)
        mois_min = date_12_mois.strftime('%Y-%m')

        revenus_bruts = db.session.query(
            Paiement.mois_concerne,
            func.sum(Paiement.montant)
        ).filter(Paiement.mois_concerne >= mois_min).group_by(
            Paiement.mois_concerne
        ).all()
        revenus_dict = dict(revenus_bruts)

        revenus_mensuels = []
        for i in range(11, -1, -1):
            mois_date = date_courante - relativedelta(months=i)
            mois_str = mois_date.strftime('%Y-%m')
            revenus_mensuels.append({
                'mois': MOIS_NOMS_COURTS[mois_date.month] + ' ' + str(mois_date.year),
                'total': revenus_dict.get(mois_str, 0) or 0
            })

        biens_stats = []
        biens = Bien.query.options(joinedload(Bien.locataires)).all()

        totaux_par_locataire = dict(db.session.query(
            Paiement.locataire_id,
            func.sum(Paiement.montant)
        ).group_by(Paiement.locataire_id).all())

        for bien in biens:
            locataire = bien.locataire_actuel
            total_percu = totaux_par_locataire.get(locataire.id, 0) or 0 if locataire else 0
            biens_stats.append({
                'bien': bien,
                'locataire': locataire,
                'total_percu': total_percu
            })

        return render_template('statistiques.html',
                             revenus_mensuels=revenus_mensuels,
                             biens_stats=biens_stats)


# ==================== INITIALISATION ====================

def _migrate_db():
    """Ajoute les colonnes manquantes pour les mises à jour."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if 'locataire' in inspector.get_table_names():
        colonnes = [col['name'] for col in inspector.get_columns('locataire')]
        migrations = {
            'raison_sociale': 'VARCHAR(200)',
            'siret': 'VARCHAR(14)',
            'dirigeant': 'VARCHAR(200)',
        }
        for col_name, col_type in migrations.items():
            if col_name not in colonnes:
                db.session.execute(text(
                    f'ALTER TABLE locataire ADD COLUMN {col_name} {col_type}'
                ))
        db.session.commit()


def init_db(app):
    """Initialise la base de données."""
    with app.app_context():
        db.create_all()
        _migrate_db()

        if Bien.query.first() is None:
            appartement = Bien(
                nom="Appartement Centre-Ville",
                type_bien="appartement",
                adresse="12 rue de la République, 75001 Paris",
                surface=65.0,
                description="Appartement T3 lumineux avec balcon",
                charges_mensuelles=150.0,
                date_acquisition=date(2020, 1, 15)
            )
            local = Bien(
                nom="Local Commercial",
                type_bien="local_commercial",
                adresse="45 avenue des Champs, 75008 Paris",
                surface=120.0,
                description="Local commercial avec vitrine, idéal commerce de proximité",
                charges_mensuelles=200.0,
                date_acquisition=date(2018, 6, 1)
            )
            db.session.add(appartement)
            db.session.add(local)
            db.session.commit()
            print("Base de données initialisée avec les biens de démonstration.")
