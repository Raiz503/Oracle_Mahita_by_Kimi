"""
╔══════════════════════════════════════════════════════════════╗
║           MOTEUR IA CONVERSATIONNEL ORACLE                   ║
║           API Groq · Mémoire · Analyses                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import re
from typing import List, Dict, Optional
from datetime import datetime

# Pour l'API Groq
try:
    from groq import Groq
    GROQ_DISPONIBLE = True
except ImportError:
    GROQ_DISPONIBLE = False

from moteur_apprentissage import moteur_apprentissage

DB_CONVERSATIONS = "oracle_conversations.json"

class MoteurIAChat:
    def __init__(self):
        self.client = None
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.conversations = self._load_conversations()
        self.contexte_foot = {}
        
        if GROQ_DISPONIBLE and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except:
                pass
    
    def _load_conversations(self) -> List[Dict]:
        if os.path.exists(DB_CONVERSATIONS):
            try:
                with open(DB_CONVERSATIONS, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_conversations(self):
        with open(DB_CONVERSATIONS, "w", encoding="utf-8") as f:
            json.dump(self.conversations[-100:], f, indent=2, ensure_ascii=False)  # Garde 100 derniers
    
    def set_contexte(self, history: Dict, saison_active: str, standings: Dict, prochaine_journee: int):
        """Met à jour le contexte football pour les réponses"""
        self.contexte_foot = {
            "saison": saison_active,
            "standings": standings,
            "prochaine_journee": prochaine_journee,
            "history": history
        }
    
    def est_connecte(self) -> bool:
        """Vérifie si l'API Groq est disponible"""
        return self.client is not None
    
    def discuter(self, message: str, user_id: str = "default") -> Dict:
        """
        Point d'entrée principal pour discuter avec l'IA
        Retourne : {"texte": str, "source": "groq"|"offline", "analyse": Dict}
        """
        # Détecte le type de demande
        type_demande = self._analyser_intention(message)
        
        # Prépare le contexte
        contexte = self._preparer_contexte()
        
        # Si connecté à Groq → utilise l'IA puissante
        if self.est_connecte():
            reponse = self._discuter_groq(message, contexte, type_demande)
            source = "groq"
        else:
            # Mode offline
            reponse = self._discuter_offline(message, type_demande)
            source = "offline"
        
        # Sauvegarde la conversation
        self._sauvegarder_echange(user_id, message, reponse["texte"])
        
        return {
            "texte": reponse["texte"],
            "source": source,
            "analyse": reponse.get("analyse", {}),
            "confiance": reponse.get("confiance", 0)
        }
    
    def _analyser_intention(self, message: str) -> str:
        """Détecte ce que l'utilisateur veut"""
        msg = message.lower()
        
        patterns = {
            "prediction": ["prono", "predi", "pronostic", "parier", "mise", "cote"],
            "analyse_match": ["analyse", "match", "versus", "vs", "contre", "affrontement"],
            "classement": ["classement", "standings", "rang", "tableau"],
            "forme": ["forme", "série", "victoire", "défaite", "série"],
            "stats": ["statistique", "stats", "pourcentage", "taux"],
            "apprentissage": ["apprend", "pattern", "découvert", "évolué"],
            "aide": ["aide", "help", "comment", "fonctionne"]
        }
        
        for intention, mots in patterns.items():
            if any(m in msg for m in mots):
                return intention
        
        return "conversation"
    
    def _preparer_contexte(self) -> str:
        """Prépare le contexte football pour l'IA"""
        ctx = []
        
        # Stats d'apprentissage
        stats = moteur_apprentissage.get_stats_apprentissage()
        ctx.append(f"📊 Stats IA : {stats['taux_reussite']}% de réussite sur {stats['total']} matchs")
        
        # Classement si dispo
        if self.contexte_foot.get("standings") is not None:
            ctx.append("\n🏆 Classement actuel (Top 5) :")
            try:
                top5 = self.contexte_foot["standings"].head(5)
                for _, row in top5.iterrows():
                    ctx.append(f"{row['Rang']}. {row['Équipe']} - {row['Pts']} pts")
            except:
                pass
        
        # Patterns découverts
        rapport = moteur_apprentissage.generer_rapport_patterns()
        ctx.append(f"\n{rapport[:800]}...")  # Limite la taille
        
        return "\n".join(ctx)
    
    def _discuter_groq(self, message: str, contexte: str, type_demande: str) -> Dict:
        """Discute via l'API Groq"""
        try:
            # Prépare le système prompt
            system_prompt = f"""Tu es Oracle Mahita, un expert en analyse footballistique et pronostics.
Tu analyses les données avec précision et donnes des prédictions chiffrées.
Tu es direct, technique mais pédagogue.

CONTEXTE ACTUEL :
{contexte}

RÈGLES :
- Toujours donner un pourcentage de confiance
- Citer les patterns découverts quand pertinent
- Si tu n'es pas sûr, le dire honnêtement
- Répondre en français"""

            # Appel API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,  # Précis, pas créatif
                max_tokens=1024
            )
            
            reponse_texte = chat_completion.choices[0].message.content
            
            # Extrait les analyses si présentes
            analyse = self._extraire_analyse(reponse_texte)
            
            return {
                "texte": reponse_texte,
                "analyse": analyse,
                "confiance": analyse.get("confiance", 70)
            }
            
        except Exception as e:
            # Fallback offline si Groq échoue
            return self._discuter_offline(message, type_demande)
    
    def _discuter_offline(self, message: str, type_demande: str) -> Dict:
        """Mode offline : réponses basées sur les règles et patterns"""
        
        if type_demande == "prediction":
            return self._reponse_offline_prediction(message)
        elif type_demande == "analyse_match":
            return self._reponse_offline_analyse(message)
        elif type_demande == "stats" or type_demande == "apprentissage":
            return self._reponse_offline_stats()
        elif type_demande == "classement":
            return self._reponse_offline_classement()
        else:
            return {
                "texte": f"🤖 **Mode Offline**\n\nJe suis limité sans connexion internet. Voici ce que je peux faire :\n\n"
                        f"• Analyser les patterns déjà appris ({moteur_apprentissage.stats_globales['total_matchs']} matchs)\n"
                        f"• Donner des stats de base\n"
                        f"• Répondre aux questions simples\n\n"
                        f"💡 **Conseil** : Connecte-toi à internet pour activer l'IA avancée (Groq).",
                "confiance": 50
            }
    
    def _reponse_offline_prediction(self, message: str) -> Dict:
        """Prédiction en mode offline basée sur les patterns"""
        # Extrait les équipes du message
        equipes = self._extraire_equipes(message)
        
        if len(equipes) >= 2:
            # Cherche dans l'historique
            h2h = self._chercher_historique(equipes[0], equipes[1])
            
            if h2h:
                return {
                    "texte": f"🤖 **Analyse Offline : {equipes[0]} vs {equipes[1]}**\n\n"
                            f"📊 Historique trouvé : {h2h['total']} matchs\n"
                            f"• Victoires {equipes[0]} : {h2h['v_dom']} ({h2h['pct_dom']}%)\n"
                            f"• Matchs nuls : {h2h['nuls']}\n"
                            f"• Victoires {equipes[1]} : {h2h['v_ext']} ({h2h['pct_ext']}%)\n\n"
                            f"💡 **Tendance** : {h2h['tendance']}\n\n"
                            f"⚠️ Mode offline - Précision limitée",
                    "confiance": 55
                }
        
        stats = moteur_apprentissage.get_stats_apprentissage()
        return {
            "texte": f"🤖 **Mode Offline**\n\n"
                    f"Je n'ai pas assez de données sur ce match en mémoire locale.\n\n"
                    f"📊 Stats globales de l'IA :\n"
                    f"• Taux de réussite : {stats['taux_reussite']}%\n"
                    f"• Matchs analysés : {stats['total']}\n\n"
                    f"💡 Connecte-toi pour une analyse complète.",
            "confiance": 40
        }
    
    def _reponse_offline_analyse(self, message: str) -> Dict:
        """Analyse détaillée offline"""
        stats = moteur_apprentissage.get_stats_apprentissage()
        rapport = moteur_apprentissage.generer_rapport_patterns()
        
        return {
            "texte": f"📊 **Analyse de l'IA (Mode Offline)**\n\n"
                    f"{rapport[:1500]}\n\n"
                    f"⚠️ Mode offline - Données limitées aux patterns stockés",
            "confiance": 60
        }
    
    def _reponse_offline_stats(self) -> Dict:
        """Stats d'apprentissage"""
        stats = moteur_apprentissage.get_stats_apprentissage()
        
        return {
            "texte": f"📊 **Performance de l'IA**\n\n"
                    f"• Matchs analysés : {stats['total']}\n"
                    f"• Taux de réussite global : {stats['taux_reussite']}%\n"
                    f"• Taux 1N2 : {stats['taux_1n2']}%\n"
                    f"• Patterns découverts : {stats['patterns_connus']}\n\n"
                    f"🔧 **Poids actuels des facteurs :**\n" +
                    "\n".join([f"• {k} : {v:.3f}" for k, v in stats['poids_actuels'].items()]),
            "confiance": 85
        }
    
    def _reponse_offline_classement(self) -> Dict:
        """Classement actuel"""
        if self.contexte_foot.get("standings") is not None:
            try:
                df = self.contexte_foot["standings"]
                lignes = ["🏆 **Classement Actuel**\n"]
                for _, row in df.iterrows():
                    emoji = "🥇" if row['Rang'] == 1 else "🥈" if row['Rang'] == 2 else "🥉" if row['Rang'] == 3 else "⚪"
                    lignes.append(f"{emoji} {row['Rang']}. {row['Équipe']} - {row['Pts']} pts (Diff: {row['Diff']:+d})")
                return {"texte": "\n".join(lignes), "confiance": 90}
            except:
                pass
        
        return {"texte": "❌ Classement non disponible en mode offline.", "confiance": 0}
    
    def _extraire_equipes(self, message: str) -> List[str]:
        """Extrait les noms d'équipes d'un message"""
        # Liste des équipes connues
        teams = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace",
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool",
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues",
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]
        
        trouvees = []
        msg_lower = message.lower()
        for team in teams:
            if team.lower() in msg_lower:
                trouvees.append(team)
        
        return trouvees
    
    def _chercher_historique(self, eq1: str, eq2: str) -> Optional[Dict]:
        """Cherche l'historique entre deux équipes"""
        history = self.contexte_foot.get("history", {})
        saison = self.contexte_foot.get("saison", "")
        
        if not history or not saison:
            return None
        
        confrontations = {"total": 0, "v_dom": 0, "v_ext": 0, "nuls": 0}
        
        for journee_data in history.get(saison, {}).values():
            for match in journee_data.get("res", []):
                h, a = match.get("h"), match.get("a")
                if (h == eq1 and a == eq2) or (h == eq2 and a == eq1):
                    confrontations["total"] += 1
                    try:
                        sh, sa = map(int, match["s"].replace("-", ":").split(":"))
                        if h == eq1:
                            if sh > sa: confrontations["v_dom"] += 1
                            elif sh < sa: confrontations["v_ext"] += 1
                            else: confrontations["nuls"] += 1
                        else:
                            if sa > sh: confrontations["v_dom"] += 1
                            elif sa < sh: confrontations["v_ext"] += 1
                            else: confrontations["nuls"] += 1
                    except:
                        pass
        
        if confrontations["total"] == 0:
            return None
        
        total = confrontations["total"]
        confrontations["pct_dom"] = round(confrontations["v_dom"] / total * 100, 1)
        confrontations["pct_ext"] = round(confrontations["v_ext"] / total * 100, 1)
        
        if confrontations["v_dom"] > confrontations["v_ext"]:
            confrontations["tendance"] = f"Avantage {eq1} à domicile"
        elif confrontations["v_ext"] > confrontations["v_dom"]:
            confrontations["tendance"] = f"Avantage {eq2} à l'extérieur"
        else:
            confrontations["tendance"] = "Match très équilibré historiquement"
        
        return confrontations
    
    def _extraire_analyse(self, texte: str) -> Dict:
        """Extrait les données structurées d'une réponse Groq"""
        analyse = {}
        
        # Cherche un pourcentage de confiance
        conf_match = re.search(r'(\d{1,3})%', texte)
        if conf_match:
            analyse["confiance"] = int(conf_match.group(1))
        
        # Cherche une prédiction 1/X/2
        pred_match = re.search(r'[Pp]ronostic.*?([1X2])', texte)
        if pred_match:
            analyse["prediction"] = pred_match.group(1)
        
        return analyse
    
    def _sauvegarder_echange(self, user_id: str, question: str, reponse: str):
        """Sauvegarde un échange dans l'historique"""
        self.conversations.append({
            "user_id": user_id,
            "question": question,
            "reponse": reponse,
            "timestamp": datetime.now().isoformat()
        })
        self.save_conversations()
    
    def get_historique_conversation(self, user_id: str = "default", limit: int = 10) -> List[Dict]:
        """Retourne l'historique récent d'une conversation"""
        return [c for c in self.conversations if c.get("user_id") == user_id][-limit:]


# Singleton
moteur_ia_chat = MoteurIAChat()
